from __future__ import annotations

import asyncio
import copy
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from pathlib import Path, PosixPath
from threading import Thread
from typing import Callable, Generator, List, Literal, Optional, Sequence, Tuple, Union
from uuid import UUID

import aiohttp

from darwin.dataset.upload_manager import LocalFile
from darwin.datatypes import PathLike
from darwin.future.core.client import ClientCore
from darwin.future.core.items.uploads import (
    async_confirm_upload,
    async_register_and_create_signed_upload_url,
    async_upload_file,
)
from darwin.future.data_objects.item import ItemSlot, UploadItem
from darwin.future.data_objects.workflow import WFDatasetCore, WFTypeCore, WorkflowCore
from darwin.future.exceptions import DarwinException, UploadFailed, UploadPending
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

    def __str__(self) -> str:
        return f"[{str(self.file)}] Status: {self.status.name}"

    def __repr__(self) -> str:
        return str(self)


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
        callback: Optional[Callable[[List[FileToStatus]], None]] = None,
    ) -> Tuple[List[Generator[FileToStatus, None, None]], Literal[None]]:
        """
        Uploads files to a dataset and optionally starts the workflow synchronously

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
        List[AsyncGenerator[FileToStatus, None]]
        """
        loop = asyncio.get_event_loop()

        output, _ = loop.run_until_complete(
            self.upload_files_async(
                files, files_to_exclude, fps, path, as_frames, extract_views, preserve_folders, auto_push, callback
            )
        )

        return output, None

    async def upload_files_async(
        self,
        files: Sequence[Union[PathLike, LocalFile]],
        files_to_exclude: Optional[List[PathLike]] = None,
        fps: int = 1,
        path: Optional[str] = None,
        as_frames: bool = False,
        extract_views: bool = False,
        preserve_folders: bool = False,
        auto_push: bool = True,  # TODO: Work out how to do this
        callback: Optional[Callable[[List[FileToStatus]], None]] = None,
    ) -> Tuple[List[Generator[FileToStatus, None, None]], Optional[asyncio.Future]]:
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
        team_slug = str(self.meta_params.get("team_slug"))  # TODO: Dogfood this works
        assert team_slug is not None

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
            team_slug,
            wf_dataset.name,
            items_and_paths,
        )

        assert len(upload_urls) == len(items_and_paths), "Upload info and items and paths should be the same length"

        updateables = [
            self._upload_updateable(team_slug, upload_url, upload_id, file.absolute(), auto_push)()
            for upload_url, upload_id, file in zip(upload_urls, upload_ids, file_paths)
        ]

        # Non blocking poller to push to next stage on completion of all.
        if auto_push:
            task = asyncio.create_task(self._upload_on_complete_actions(updateables, auto_push, callback))
            return updateables, task

        return updateables, None

    async def _upload_on_complete_actions(
        self,
        items: List[Generator[FileToStatus, None, None]],
        auto_push: bool,
        callback: Optional[Callable[[List[FileToStatus]], None]] = None,
    ) -> None:
        """
        (internal) Polls the upload status of a list of files and performs actions on completion

        Arguments
        ---------
        items: List[Generator[FileToStatus, None, None]]
            The files to poll
        auto_push: bool
            Whether to automatically push the files to the next stage
        callback: Optional[Callable[[List[FileToStatus]], None]]
            A callback to run on completion

        Returns
        -------
        None
        """
        MAX_ITERATIONS = 100
        iteration_count = 0

        if not auto_push and not callback:
            return

        while True and iteration_count <= MAX_ITERATIONS:
            if all(next(item).status == UploadStatus.UPLOADED for item in items):
                if auto_push:
                    self.push_from_dataset_stage()

                if callback:
                    outputs = [next(item) for item in items]
                    callback(outputs)

                break
            iteration_count += 1
            await asyncio.sleep(1)

    def _upload_updateable(
        self, team_slug: str, upload_url: str, upload_id: str, file: Path, auto_push: bool
    ) -> Callable[..., Generator[FileToStatus, None, None]]:
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
        # Partials need to use a method from self without sharing reference in memory
        cached_self = copy.deepcopy(self)

        def updateable() -> Generator[FileToStatus, None, None]:
            loop = asyncio.get_event_loop()
            file_status = FileToStatus(file, upload_id, UploadStatus.PENDING)

            # If file doesn't exist, we can never upload it, so always return FILE_DOES_NOT_EXIST
            if not file.exists():
                file_status.status = UploadStatus.FILE_DOES_NOT_EXIST
                while True:
                    yield file_status

            # Perform the upload
            response = loop.run_until_complete(self._upload_file_to_signed_url(upload_url, file))
            if response.status != 200:
                file_status.status = UploadStatus.FAILED
                while True:
                    yield file_status

            file_status.status = cached_self._updateable_wait(cached_self, loop, team_slug, upload_id, file_status)

            if file_status.status == UploadStatus.FAILED:
                while True:
                    yield file_status

            file_status.status = UploadStatus.UPLOADED
            yield file_status

        return updateable

    @classmethod
    def _updateable_wait(
        cls,
        self: Workflow,
        loop: asyncio.AbstractEventLoop,
        team_slug: str,
        upload_id: str,
        file_status: FileToStatus,
    ) -> UploadStatus:
        start_time = loop.time()
        THREE_MINUTES = 60 * 3

        while loop.time() - start_time < THREE_MINUTES:
            try:
                client = ClientCore(self.client.config)
                loop.run_until_complete(
                    async_confirm_upload(
                        client,
                        team_slug,
                        upload_id,
                    )
                )
            except UploadPending:
                continue
            except UploadFailed:
                file_status.status = UploadStatus.FAILED
                break
            except Exception as exc:
                logger.error(f"Error while uploading file {file_status.file} to {upload_id}", exc_info=exc)
                file_status.status = UploadStatus.FAILED
                break
            else:
                loop.run_until_complete(asyncio.sleep(0.3))

        return file_status.status

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

        relative_path = file.relative_to(root_path).parent
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
        try:
            assert all(isinstance(path, Path) for path in paths), "paths must be a list of Path objects"
        except AssertionError as exc:
            raise ValueError("paths must be a list of Path objects") from exc

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

    async def _upload_file_to_signed_url(self, url: str, file: Path) -> aiohttp.ClientResponse:
        """
        Uploads a file to a signed URL

        Arguments
        ---------
        url: str
            The signed URL to upload to
        file: PathLike
            The file to upload
        """
        upload = await async_upload_file(self.client, url, file)

        if not upload.ok:
            raise DarwinException(f"Failed to upload file {file} to {url}", upload)

        return upload
