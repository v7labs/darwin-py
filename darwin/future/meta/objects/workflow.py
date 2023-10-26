from __future__ import annotations

import asyncio
import logging
from enum import Enum, auto
from pathlib import Path, PosixPath
from typing import AsyncGenerator, List, Optional, Sequence, Tuple, Union
from uuid import UUID

import httpx

from darwin.dataset.upload_manager import LocalFile
from darwin.datatypes import PathLike
from darwin.future.core.client import ClientCore
from darwin.future.core.items.uploads import (
    async_register_and_create_signed_upload_url,
    confirm_upload,
)
from darwin.future.core.team.get_team import get_team
from darwin.future.data_objects.item import ItemSlot, UploadItem
from darwin.future.data_objects.workflow import WFDatasetCore, WFTypeCore, WorkflowCore
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery

logger = logging.getLogger(__name__)


class FileToStatus:
    def __init__(self, file: Path, upload_id: str, status: UploadStatus):
        self.file = file
        self.upload_id = upload_id
        self.status = status

    file: Path
    upload_id: str
    status: UploadStatus


class UploadStatus(Enum):
    PENDING = auto()
    FILE_DOES_NOT_EXIST = auto()
    UPLOADING = auto()
    UPLOADED = auto()
    FAILED = auto()


class Workflow(MetaBase[WorkflowCore]):
    """
    Workflow Meta object. Facilitates the creation of Query objects, lazy loading of
    sub fields

    Args:
        MetaBase (Workflow): Generic MetaBase object expanded by Workflow core object
            return type

    Returns:
        _type_: Workflow

    Attributes:
        name (str): The name of the workflow.
        id (UUID): The id of the workflow
        datasets (List[Dataset]): A list of datasets associated with the workflow.
        stages (StageQuery): Queries stages associated with the workflow.

    Methods:
        push_from_dataset_stage() -> Workflow:
            moves all items associated with the dataset stage to the next connected stage
        upload_files(...): -> Workflow:
            Uploads files to the dataset stage of the workflow

    Example Usage:
        # Get the workflow object
        workflow = client.team.workflows.where(name='test').collect_one()

        # Get the stages associated with the workflow
        stages = workflow.stages

        # Get the datasets associated with the workflow
        datasets = workflow.datasets
    """

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

    def __str__(self) -> str:
        return f"Workflow\n\
- Workflow Name: {self._element.name}\n\
- Workflow ID: {self._element.id}\n\
- Connected Dataset ID: {self.datasets[0].id}\n\
- Conneted Dataset Name: {self.datasets[0].name}"

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
    ) -> List[AsyncGenerator[FileToStatus, None]]:
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
        path: Optional[str] = None,  # TODO: Apply this to files
        as_frames: bool = False,
        extract_views: bool = False,
        preserve_folders: bool = False,
        auto_push: bool = True,  # TODO: Work out how to do this
    ) -> List[AsyncGenerator[FileToStatus, None]]:
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

        core_client = ClientCore(self.client.config)
        wf_dataset: WFDatasetCore = self._element.dataset
        wf_team = get_team(core_client, str(self._element.team_id))  # TODO: This may or may not work, test it

        file_paths = await self._convert_filelikes_to_paths(files)
        if files_to_exclude is not None:
            file_paths = [f for f in file_paths if f not in files_to_exclude]

        root_path, root_paths_absolute = self._derive_root_path(file_paths)

        upload_items = await self._prepare_upload_items(
            path or "/", root_path, file_paths, as_frames, fps, extract_views, preserve_folders
        )

        items_and_paths: List[Tuple[UploadItem, Path]] = (
            list(zip(upload_items, [root_paths_absolute])) if preserve_folders else list(zip(upload_items, [Path("/")]))
        )

        # This is one API call, so we can't create a multiple output for it
        upload_urls, upload_ids = await async_register_and_create_signed_upload_url(
            ClientCore(self.client.config),
            wf_team.slug,
            wf_dataset.name,
            items_and_paths,
        )

        assert len(upload_urls) == len(items_and_paths), "Upload info and items and paths should be the same length"

        return [
            self._upload_updateable(upload_url, upload_id, file.absolute())
            for upload_url, upload_id, file in zip(upload_urls, upload_ids, file_paths)
        ]

        # if auto_push:
        #     self.push_from_dataset_stage()
        # return self

    async def _upload_updateable(
        self, upload_url: str, upload_id: str, file: Path
    ) -> AsyncGenerator[FileToStatus, None]:
        """
        Uploads a file to a signed URL

        Arguments
        ---------
        url: str
            The signed URL to upload to
        file: PathLike
            The file to upload

        Returns
        -------
        Generator
            A generator that will update the upload status
        """
        file_status = FileToStatus(file, upload_id, UploadStatus.PENDING)

        # If file doesn't exist, we can never upload it, so always return FILE_DOES_NOT_EXIST
        if not file.exists():
            file_status.status = UploadStatus.FILE_DOES_NOT_EXIST
            while True:
                yield file_status

        # Perform the upload
        response = await self._upload_file_to_signed_url(upload_url, file)
        if response.status_code != 200:
            file_status.status = UploadStatus.FAILED
            while True:
                yield file_status

        # Status not UPLOADED until we have run the confirm_upload
        yield file_status

        try:
            client = ClientCore(self.client.config)
            confirm_upload(
                client,
                self.client.config.default_team,  # TODO Figure this out,
                upload_id,
            )
        except requests.exceptions.HTTPError as exc:
            if exc.response and exc.response.status_code == 404:
                file_status.status = UploadStatus.PENDING
            else:
                raise exc

        file_status.status = UploadStatus.UPLOADED
        yield file_status

    @classmethod
    async def _prepare_upload_items(
        cls,
        imposed_path: str,
        root_path: Path,
        file_paths: List[Path],
        as_frames: bool,
        fps: int,
        extract_views: bool,
        preserve_folders: bool,
    ) -> List[UploadItem]:
        """
        (internal) Prepares a list of files to be uploaded

        Arguments
        ---------
        imposed_path: str
            The path to impose on the files on the server
            e.g. a file at ./this/path/1.jpg with imposed path of /location
            will go to /location/1.jpg, or /location/this/path/1.jpg if
            preserve_folders is True
        path: Path
            The path to the (relative) lowest root of the files.
            - Must be a folder path
            - Must be a parent of all files
        file_paths: List[Path]
            The actual files to upload.  These must be absolute, existing objects
            on the local filesystem
        as_frames: bool
            Whether to upload video files as frames
        fps: int
            Frames per second for video files
        extract_views: bool
            Whether to extract views from video files
        preserve_folders: bool
            Whether to preserve the folder structure when uploading

        Returns
        -------
        List[UploadItem]
            The files as UploadItems

        """
        assert root_path.is_dir(), "root_path must be a directory"
        assert all(
            file.is_absolute() and file.is_file() and file.exists() for file in file_paths
        ), "file_paths must be absolute paths"

        return [
            UploadItem(
                name=file.name,
                path=cls._get_item_path(file, root_path, imposed_path, preserve_folders),
                slots=[
                    ItemSlot(
                        slot_name=str(index),
                        file_name=file.name,
                        as_frames=as_frames,
                        fps=fps,
                        extract_views=extract_views,
                    )
                ],
            )
            for index, file in enumerate(file_paths)
        ]

    @classmethod
    def _get_item_path(cls, file: Path, root_path: Path, imposed_path: str, preserve_folders: bool) -> str:
        """
        (internal) Returns the parent path a file should be stored at on the server

        ex. file = /this/path/1.jpg
            root_path = /this
            imposed_path = /location
            preserve_folders = True
            returns /location/path/

        ex. file = /this/path/1.jpg
            root_path = /this
            imposed_path = /location
            preserve_folders = False
            returns /

        Arguments
        ---------
        file: Path
            The file to upload
        root_path: Path
            The path to the (relative) lowest root of the files.
            - Must be a folder path
            - Must be a parent of all files
        imposed_path: str
            The path to impose on the files on the server
            e.g. a file at ./this/path/1.jpg with imposed path of /location
            will go to /location/1.jpg, or /location/this/path/1.jpg if
            preserve_folders is True
        preserve_folders: bool
            Whether to preserve the folder structure when uploading

        Returns
        -------
        str
            The path to the file on the server
        """
        try:
            PosixPath(imposed_path).resolve()
        except Exception as exc:
            raise ValueError("imposed_path must be a valid PosixPath") from exc

        assert root_path.is_dir(), "root_path must be a directory"
        assert (
            file.is_absolute() and file.is_file() and file.exists()
        ), "file must be an absolute path to an existing file"

        relative_path = file.relative_to(root_path)
        path = Path(imposed_path) / relative_path if preserve_folders else Path(imposed_path)

        return_path = str(path)
        if return_path == ".":
            return "/"

        if not return_path.startswith("/"):
            return_path = "/" + return_path

        return return_path

    @classmethod
    def _derive_root_path(cls, paths: List[Path]) -> Tuple[Path, Path]:
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
        assert all(isinstance(path, Path) for path in paths), "paths must be a list of Path objects"

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

        def convert_to_path(file: Union[PathLike, LocalFile]) -> Path:
            if isinstance(file, LocalFile):
                return Path(file.local_path)
            return Path(file)

        return [convert_to_path(f) for f in files]

    @classmethod
    async def _upload_file_to_signed_url(cls, url: str, file: Path) -> requests.Response:
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

        with httpx.AsyncClient() as client:

        files = {"file": open(file, "rb")}
        return requests.post(url, files=files)
