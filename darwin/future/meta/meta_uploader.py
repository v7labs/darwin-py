from __future__ import annotations

from collections import namedtuple
from pathlib import Path, PosixPath
from typing import List, Optional, Sequence, Set, Tuple, cast
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
    ItemCore,
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


# TODO: Test this
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


# TODO: Test this
def _initialise_item_uploads(upload_items: List[UploadItem]) -> List[ItemUpload]:
    """
    (internal) Initialises a list of ItemUploads

    Arguments
    ---------
    upload_items: List[UploadItem]
        The upload items to initialise

    Returns
    -------
    List[ItemUpload]
        The initialised ItemUploads
    """
    return [
        ItemUpload(
            upload_item=upload_item,
            status=ItemUploadStatus.PENDING,
        )
        for upload_item in upload_items
    ]


# TODO: Test this
def _initialise_items_and_paths(
    upload_items: List[UploadItem], root_path_absolute: Path, item_payload: ItemCreate
) -> List[Tuple[UploadItem, Path]]:
    """
    (internal) Initialises a list of ItemUploads

    Arguments
    ---------
    upload_items: List[UploadItem]
        The upload items to initialise

    Returns
    -------
    List[ItemUpload]
        The initialised ItemUploads
    """
    return (
        list(zip(upload_items, [root_path_absolute]))
        if item_payload.preserve_folders
        else list(zip(upload_items, [Path("/")]))
    )


def _update_item_upload(
    item_upload: ItemUpload,
    status: Optional[ItemUploadStatus] = None,
    upload_url: Optional[str] = None,
    upload_id: Optional[str | UUID] = None,
    upload_item: Optional[UploadItem] = None,
    path: Optional[Path] = None,
    item: Optional[Item] = None,
) -> ItemUpload:
    """
    (internal) Updates an ItemUpload

    Arguments
    ---------
    item_upload: ItemUpload
        The ItemUpload to update
    status: Optional[ItemUploadStatus]
        The status to update the ItemUpload to
    upload_url: Optional[str]
        The upload URL to update the ItemUpload to
    upload_id: Optional[str | UUID]
        The upload ID to update the ItemUpload to
    upload_item: Optional[UploadItem]
        The UploadItem to update the ItemUpload to
    path: Optional[Path]
        The path to update the ItemUpload to
    item: Optional[Item]
        The Item to update the ItemUpload to

    Returns
    -------
    ItemUpload
        The updated ItemUpload
    """
    if status is not None:
        item_upload.status = status

    if upload_url is not None:
        item_upload.url = upload_url

    if upload_id is not None:
        if isinstance(upload_id, str):
            item_upload.id = UUID(upload_id)
        else:
            item_upload.id = upload_id

    if upload_item is not None:
        item_upload.upload_item = upload_item

    if path is not None:
        item_upload.path = path

    if item is not None:
        item_upload.item = item

    return item_upload


# TODO: Test this
def _item_dict_to_item(client: ClientCore, item_dict: dict) -> Item:
    """
    (internal) Converts an item dict to an item

    Arguments
    ---------
    item_dict: dict
        The item dict to convert

    Returns
    -------
    Item
        The converted item
    """
    item_core = ItemCore(
        # Key accesses for required members
        name=item_dict["name"],
        id=item_dict["id"],
        slots=item_dict["slots"],
        path=item_dict["path"],
        dataset_id=item_dict["dataset_id"],
        processing_status=item_dict["processing_status"],
        # `get` accesses for optional members
        archived=item_dict.get("archived"),
        priority=item_dict.get("priority"),
        tags=item_dict.get("tags"),
        layout=item_dict.get("layout"),
    )
    return Item(
        element=item_core,
        client=client,
    )


def _items_dicts_to_items(client: ClientCore, items_dicts: List[dict]) -> List[Item]:
    """
    (internal) Converts a list of item dicts to a list of items

    Arguments
    ---------
    items_dicts: List[dict]
        The item dicts to convert

    Returns
    -------
    List[Item]
        The converted items
    """
    return [_item_dict_to_item(client, item_dict) for item_dict in items_dicts]


# TODO: Test this
def _initial_items_and_blocked_items(
    client: ClientCore, item_uploads: List[ItemUpload], items_dicts: List, blocked_items_dicts: List
) -> Tuple[List[Item], List[Item]]:
    return _items_dicts_to_items(client, items_dicts), _items_dicts_to_items(client, blocked_items_dicts)


async def _handle_uploads(client: ClientCore, item_uploads: List[ItemUpload]) -> None:
    for item_upload in item_uploads:
        item_upload.status = ItemUploadStatus.UPLOADING
        try:
            assert item_upload.path is not None
            assert item_upload.url is not None
        except AssertionError as exc:
            raise DarwinException("ItemUpload must have a path and url") from exc

        await _upload_file_to_signed_url(client, item_upload.url, item_upload.path)
        item_upload.status = ItemUploadStatus.UPLOADED


async def _confirm_uploads(client: ClientCore, team_slug: str, item_uploads: List[ItemUpload]) -> None:
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


CombinedUploaderResult = namedtuple("CombinedUploaderResult", ["item_uploads", "items", "blocked_items"])


# TODO: Test this
async def combined_uploader(
    client: ClientCore,
    team_slug: str,
    dataset_id: int,
    item_payload: ItemCreate,
) -> CombinedUploaderResult:
    """
    Uploads a list of files to a dataset

    Parameters
    ----------
    client : Client
        The client to use to make the request
    dataset : Dataset
        The dataset to upload the files to
    item_payload : ItemCreate
        The item payload to create the item with.

    Returns
    -------
    List[ItemUpload]
        The uploaded items

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

    item_uploads = _initialise_item_uploads(upload_items)

    if item_payload.callback_when_loading:
        item_payload.callback_when_loading(item_uploads)

    # 3. Register and create signed upload url
    items_and_paths = _initialise_items_and_paths(upload_items, root_paths_absolute, item_payload)
    upload_urls, upload_ids, items_dicts, blocked_items_dicts = await async_register_and_create_signed_upload_url(
        client,
        team_slug,
        dataset.name,
        items_and_paths,
    )

    items, blocked_items = _initial_items_and_blocked_items(client, item_uploads, items_dicts, blocked_items_dicts)

    [
        (
            _update_item_upload(
                item_upload,
                upload_url=upload_url,
                upload_id=upload_id,
                upload_item=upload_item,
                path=path,
                item=item,
            )
            for upload_url, upload_id, (upload_item, path), item, item_upload in zip(
                upload_urls, upload_ids, items_and_paths, items, item_uploads
            )
        )
    ]

    await _handle_uploads(client, item_uploads)

    if item_payload.callback_when_loading:
        item_payload.callback_when_loading(item_uploads)

    await _confirm_uploads(client, team_slug, item_uploads)

    if item_payload.callback_when_loaded:
        item_payload.callback_when_loaded(item_uploads)

    return CombinedUploaderResult(item_uploads, items, blocked_items)

    # ? Handle blocked items
