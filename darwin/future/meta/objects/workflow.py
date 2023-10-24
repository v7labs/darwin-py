from __future__ import annotations

import asyncio
import logging
from collections import namedtuple
from distutils.command import upload
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union
from uuid import UUID

import requests

from darwin.dataset.upload_manager import LocalFile
from darwin.datatypes import PathLike
from darwin.future.core.client import ClientCore
from darwin.future.core.items.uploads import async_register_and_create_signed_upload_url
from darwin.future.data_objects.item import ItemSlot, UploadItem
from darwin.future.data_objects.workflow import WFDatasetCore, WFTypeCore, WorkflowCore
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery

logger = logging.getLogger(__name__)


FilesToStatus = namedtuple("FilesToStatus", ["file", "status"])


class Workflow(MetaBase[WorkflowCore]):
    @property
    def stages(self) -> StageQuery:
        meta_params = self.meta_params.copy()
        meta_params["workflow_id"] = self._element.id
        if self.datasets is not None:
            meta_params["dataset_id"] = self.datasets[0].id
            meta_params["dataset_name"] = self.datasets[0].name
        return StageQuery(self.client, meta_params=meta_params)

    @property
    def datasets(self) -> List[WFDatasetCore]:
        if self._element.dataset is None:
            raise ValueError("WorkflowMeta has no associated dataset")
        return [self._element.dataset]

    @property
    def id(self) -> UUID:
        return self._element.id

    @property
    def name(self) -> str:
        return self._element.name

    def push_from_dataset_stage(self) -> Workflow:
        assert self._element.dataset is not None
        stages = self.stages
        ds_stage = stages[0]
        assert len(stages) > 1
        assert ds_stage._element.type == WFTypeCore.DATASET
        next_stage = ds_stage._element.edges[0].target_stage_id
        assert next_stage is not None
        ds_stage.move_attached_files_to_stage(next_stage)
        return self

    def upload_files(
        self,
        files: Sequence[Union[PathLike, LocalFile]],
        files_to_exclude: Optional[List[PathLike]] = None,
        fps: int = 1,
        path: Optional[str] = None,
        as_frames: bool = False,
        extract_views: bool = False,
        preserve_folders: bool = False,
        auto_push: bool = True,
    ) -> List[FilesToStatus]:
        return asyncio.run(
            self.upload_files_async(
                files,
                files_to_exclude,
                fps,
                path,
                as_frames,
                extract_views,
                preserve_folders,
                auto_push,
            )
        )

    async def upload_files_async(
        self,
        files: Sequence[Union[PathLike, LocalFile]],
        files_to_exclude: Optional[List[PathLike]] = None,
        fps: int = 1,
        path: Optional[str] = None,
        as_frames: bool = False,
        extract_views: bool = False,
        preserve_folders: bool = False,
        auto_push: bool = True,
    ) -> List[FilesToStatus]:
        """
        Uploads files to a dataset and optionally starts the workflow

        Arguments
        ---------
        files: Sequence[Union[PathLike, LocalFile]]
            The files to upload
        files_to_exclude: Optional[List[PathLike]]
            Files to exclude from the upload
        fps: int
            Frames per second for video files
        path: Optional[str]
            Path to upload the files to
        as_frames: bool
            Whether to upload video files as frames
        extract_views: bool
            Whether to extract views from video files
        preserve_folders: bool
            Whether to preserve the folder structure when uploading
        auto_push: bool
            Whether to automatically push the files to the next stage

        Returns
        -------
        List[FilesToStatus]
            A list of files and their upload status
        """

        assert self._element.dataset is not None

        wf_dataset: WFDatasetCore = self._element.dataset
        wf_team = ""  # TODO Figure this out

        file_paths = await self._convert_filelikes_to_paths(files)
        root_path, root_path_absolute = await self._derive_root_path(file_paths)

        upload_items = await self._prepare_upload_items(
            root_path_absolute,
            file_paths,
            as_frames,
            fps,
            extract_views,
        )

        items_and_paths: List[Tuple[UploadItem, Path]] = (
            list(zip(upload_items, file_paths)) if preserve_folders else list(zip(upload_items, [Path("/")]))
        )

        # This is one API call, so we can't create a multiple output for it
        upload_urls, upload_ids = await async_register_and_create_signed_upload_url(
            ClientCore(self.client.config),
            self.client.config.default_team,  # TODO Figure this out,
            wf_dataset.name,
            items_and_paths,
        )

        # TODO: Upload files to the signed URLs

        # TODO: Return list of generators that will update the status of the files

        # 1. Upload files to dataset
        #   a. If preserve folders, use the root path to do this.
        #   b. If not, upload all to root
        # 2. return list of files and their status - status being a generator that will update

        return []

        # if auto_push:
        #     self.push_from_dataset_stage()
        # return self

    @classmethod
    async def _prepare_upload_items(
        cls,
        root_path_absolute: Path,
        file_paths: List[Path],
        as_frames: bool,
        fps: int,
        extract_views: bool,
    ) -> List[UploadItem]:
        return [
            UploadItem(
                name=f.name,
                path=str(f.relative_to(root_path_absolute)),
                slots=[
                    ItemSlot(
                        slot_name=str(i),
                        file_name=f.name,
                        as_frames=as_frames,
                        fps=fps,
                        extract_views=extract_views,
                    )
                ],
            )
            for i, f in enumerate(file_paths)
        ]

    @classmethod
    async def _derive_root_path(cls, paths: List[Path]) -> Tuple[Path, Path]:
        """
        Finds the lowest common path in a set of paths

        Arguments
        ---------
        files: Sequence[Union[PathLike, LocalFile]]
            The set of paths to search

        Returns
        -------
        Tuple[Path, Path]
            The lowest common path to the current working directory, both as a relative path, and an absolute path
        """

        root_path = paths[0]

        for path in paths:
            if len(path.parts) < len(root_path.parts):
                root_path = path

        return Path(root_path.stem), Path(root_path.stem).resolve()

    @classmethod
    async def _convert_filelikes_to_paths(cls, files: Sequence[Union[PathLike, LocalFile]]) -> List[Path]:
        """
        Converts a list of files to a list of paths

        Arguments
        ---------
        files: Sequence[Union[PathLike, LocalFile]]
            The files to convert

        Returns
        -------
        List[Path]
            The files as paths
        """

        return [Path(str(f)) for f in files]

    @classmethod
    def upload_file_to_signed_url(cls, url: str, file: PathLike) -> requests.Response:
        """
        Uploads a file to a signed URL

        Arguments
        ---------
        url: str
            The signed URL to upload to
        file: PathLike
            The file to upload
        """
        # TODO: Initial naive implementation, needs to be improved
        # should be async, maybe use aiohttp?

        files = {"file": open(file, "rb")}
        return requests.post(url, files=files)
