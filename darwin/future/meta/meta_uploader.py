from __future__ import annotations

from pathlib import Path, PosixPath
from typing import List, Sequence, Set, Tuple, cast
from uuid import UUID

import aiohttp

from darwin.future.core.client import ClientCore
from darwin.future.core.datasets import get_dataset
from darwin.future.core.items.uploads import (
    async_confirm_upload,
    async_register_and_create_signed_upload_url,
    async_upload_file,
)
from darwin.future.data_objects.item import (
    ItemCreate,
    ItemSlot,
    ItemUpload,
    ItemUploadStatus,
    UploadItem,
)
from darwin.future.exceptions import DarwinException, UploadPending
from darwin.future.meta.objects.item import Item


def _get_item_path(file: Path, root_path: Path, imposed_path: str, preserve_folders: bool) -> str:
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

    Parameters
    ----------
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
        # Seems counterintuitive, but this is for _remote_ storage, which is POSIX type
        PosixPath(imposed_path).resolve()
    except Exception as exc:
        raise ValueError("imposed_path must be a valid PosixPath") from exc

    assert root_path.is_dir(), "root_path must be a directory"
    assert file.is_absolute() and file.is_file() and file.exists(), "file must be an absolute path to an existing file"

    relative_path = file.relative_to(root_path).parent
    path = Path(imposed_path) / relative_path if preserve_folders else Path(imposed_path)

    return_path = str(path)
    if return_path == ".":
        return "/"

    if not return_path.startswith("/"):
        return_path = "/" + return_path

    return return_path


async def _prepare_upload_items(
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
            path=_get_item_path(file, root_path, imposed_path, preserve_folders),
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


def _derive_root_path(paths: List[Path]) -> Tuple[Path, Path]:
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


async def _create_list_of_all_files(files_to_upload: Sequence[Path], files_to_exclude: Sequence[Path]) -> List[Path]:
    """
    (internal) Creates a flat list of all files to upload from a list of files or file paths and a
    list of files or file paths to exclude

    Arguments
    ---------
    files_to_upload: Sequence[Path]
        The files to upload
    files_to_exclude: Sequence[Path]
        The files to exclude from the upload

    Returns
    -------
    List[Path]
        The list of files to upload
    """
    master_files_to_upload: Set[Path] = set()

    for file in files_to_upload:
        files = file.glob("**/*") if file.is_dir() else [file]
        master_files_to_upload.update(files)

    for file in files_to_exclude:
        files = file.glob("**/*") if file.is_dir() else [file]
        master_files_to_upload.difference_update(files)

    return list(master_files_to_upload)


async def combined_uploader(
    client: ClientCore,
    team_slug: str,
    dataset_id: int,
    item_payload: ItemCreate,
) -> List[Item]:
    """
    (internal) Uploads a list of files to a dataset

    Parameters
    ----------
    client : Client
        The client to use to make the request
    dataset : Dataset
        The dataset to upload the files to
    item_payload : ItemCreate
        The item payload to create the item with.
    use_folders : bool
    """

    dataset = get_dataset(client, str(dataset_id))

    files_to_upload = await _create_list_of_all_files(item_payload.files, item_payload.files_to_exclude or [])
    root_path, root_paths_absolute = _derive_root_path(files_to_upload)

    # 2. Prepare upload items
    upload_items = await _prepare_upload_items(
        item_payload.path or "/",
        root_path,
        files_to_upload,
        item_payload.as_frames or False,
        cast(int, item_payload.fps),
        item_payload.extract_views or False,
        item_payload.preserve_folders or False,
    )

    item_uploads = [
        ItemUpload(
            upload_item=upload_item,
            status=ItemUploadStatus.PENDING,
        )
        for upload_item in upload_items
    ]

    if item_payload.callback_when_loading:
        item_payload.callback_when_loading(item_uploads)

    # 3. Register and create signed upload url
    items_and_paths: List[Tuple[UploadItem, Path]] = (
        list(zip(upload_items, [root_paths_absolute]))
        if item_payload.preserve_folders
        else list(zip(upload_items, [Path("/")]))
    )
    upload_urls, upload_ids = await async_register_and_create_signed_upload_url(
        client,
        team_slug,
        dataset.name,
        items_and_paths,
    )

    # TODO Extract this into a function
    def apply_info(
        item_upload: ItemUpload, upload_url: str, upload_id: str, upload_item: UploadItem, path: Path
    ) -> ItemUpload:
        item_upload.id = UUID(upload_id)
        item_upload.url = upload_url
        item_upload.upload_item = upload_item
        item_upload.path = path
        return item_upload

    [
        apply_info(item_upload, upload_url, upload_id, upload_item, path)
        for upload_url, upload_id, (upload_item, path), item_upload in zip(
            upload_urls, upload_ids, items_and_paths, item_uploads
        )
    ]

    # 5. Upload files
    # TODO Extract this into a function
    for item_upload in item_uploads:
        item_upload.status = ItemUploadStatus.UPLOADING
        try:
            assert item_upload.path is not None
            assert item_upload.url is not None
        except AssertionError as exc:
            raise DarwinException("ItemUpload must have a path and url") from exc

        await _upload_file_to_signed_url(client, item_upload.url, item_upload.path)
        item_upload.status = ItemUploadStatus.UPLOADED

    if item_payload.callback_when_loading:
        item_payload.callback_when_loading(item_uploads)

    # 7. Confirm upload
    # TODO Extract this into a function
    MAX_RETRIES = 10
    retry_count = 0
    while any(item.status == ItemUploadStatus.PENDING for item in item_uploads):
        for item in item_uploads:
            try:
                await async_confirm_upload(client, team_slug, str(item.id))
            except UploadPending as exc:
                item.status = ItemUploadStatus.PENDING
                raise exc
            else:
                item.status = ItemUploadStatus.PROCESSING
        if retry_count >= MAX_RETRIES:
            raise DarwinException("Upload timed out")
        retry_count += 1

    if item_payload.callback_when_loaded:
        item_payload.callback_when_loaded(item_uploads)

    # Do other stuff

    # 10. Await completion polling
    # 11. Send results to callback
    # 13. Retrieve items
    # 14. Return items

    # ? Handle blocked items
    ...
