import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Union

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.item import Item
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import DarwinException


async def _build_slots(item: Item) -> List[Dict]:
    """
    (internal) Builds the slots for an item

    Parameters
    ----------
    item: Item
        The item to build slots for

    Returns
    -------
    List[Dict]
        The built slots
    """
    # ! testme

    if not item.slots:
        return []

    slots_to_return: List[Dict] = []

    for slot in item.slots:
        slot_dict: Dict[str, UnknownType] = {
            "slot_name": slot.slot_name,
            "file_name": slot.file_name,
            "storage_key": slot.storage_key,
            "fps": slot.fps,
            "type": slot.type,
        }

        if slot.as_frames is not None:
            slot_dict["as_frames"] = slot.as_frames

        if slot.extract_views is not None:
            slot_dict["extract_views"] = slot.extract_views

        if slot.metadata is not None:
            slot_dict["metadata"] = slot.metadata

        if slot.tags is not None:
            slot_dict["tags"] = slot.tags

        slots_to_return.append(slot_dict)

    return slots_to_return


async def _build_layout(item: Item) -> Dict:
    if not item.layout:
        return {}

    if item.layout.version == 1:
        return {
            "slots": item.layout.slots,
            "type": item.layout.type,
            "version": item.layout.version,
        }

    if item.layout.version == 2:
        return {
            "slots": item.layout.slots,
            "type": item.layout.type,
            "version": item.layout.version,
            "layout_shape": item.layout.layout_shape,
        }

    raise DarwinException(f"Invalid layout version {item.layout.version}")


async def _build_payload_items(items_and_paths: List[Tuple[Item, Path]]) -> List[Dict]:
    """
    Builds the payload for the items to be registered for upload

    Parameters
    ----------
    items_and_paths: List[Tuple[Item, Path]]

    Returns
    -------
    List[Dict]
        The payload for the items to be registered for upload
    """

    return_list = []
    for item, path in items_and_paths:
        base_item = {
            "name": getattr(item, "name"),
            "path:": str(path),
            "tags": getattr(item, "tags", []),
        }

        if getattr(item, "slots", None):
            base_item["slots"] = await _build_slots(item)

        if getattr(item, "layout", None):
            base_item["layout"] = await _build_layout(item)

        return_list.append(base_item)

    return return_list


async def async_register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[Tuple[Item, Path], List[Tuple[Item, Path]]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> JSONType:
    """
    Registers an upload for a dataset that can then be used to upload files to Darwin

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to register the upload for
    dataset_slug: str
        The slug of the dataset to register the upload for
    items_and_paths: Union[Tuple[Item, Path], List[Tuple[Item, Path]]]
        A list of tuples of Items and Paths to register for upload
    force_tiling: bool
        Whether to force tiling for the upload
    handle_as_slices: bool
        Whether to handle the upload as slices
    ignore_dicom_layout: bool
        Whether to ignore the dicom layout
    """

    if isinstance(items_and_paths, tuple):
        items_and_paths = [items_and_paths]
        assert all(
            (isinstance(item, Item) and isinstance(path, Path)) for item, path in items_and_paths
        ), "items must be a list of Items"

    payload_items = await _build_payload_items(items_and_paths)

    options = {
        "force_tiling": force_tiling,
        "handle_as_slices": handle_as_slices,
        "ignore_dicom_layout": ignore_dicom_layout,
    }

    payload = {
        "dataset_slug": dataset_slug,
        "items": payload_items,
        "options": options,
    }

    return api_client.post(f"/api/v2/teams/{team_slug}/items/register_upload", payload)


async def async_create_signed_upload_url(
    api_client: ClientCore,
    upload_id: str,
    team_slug: str,
) -> JSONType:
    """
    Asynchronously create a signed upload URL for an upload or uploads

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to register the upload for
    upload_id: str
        The ID of the upload to confirm

    Returns
    -------
    JSONType
        The response from the API
    """
    # TODO: Test me
    return api_client.post(f"/api/v2/teams/{team_slug}/items/uploads/{upload_id}/sign", data={})


async def async_register_and_create_signed_upload_url(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[Tuple[Item, Path], List[Tuple[Item, Path]]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> JSONType:
    """
    Asynchronously register and create a signed upload URL for an upload or uploads

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to register the upload for
    dataset_slug: str
        The slug of the dataset to register the upload for
    items_and_paths: Union[Tuple[Item, Path], List[Tuple[Item, Path]]]
        A list of tuples, or a single tuple of Items and Paths to register for upload
    force_tiling: bool
        Whether to force tiling for the upload
    handle_as_slices: bool
        Whether to handle the upload as slices
    ignore_dicom_layout: bool
        Whether to ignore the dicom layout

    Returns
    -------
    JSONType
        The response from the API
    """
    # TODO: test me
    register = (
        await async_register_upload(
            api_client,
            team_slug,
            dataset_slug,
            items_and_paths,
            force_tiling,
            handle_as_slices,
            ignore_dicom_layout,
        ),
    )

    download_id = getattr(register, "id")
    if "errors" in register or not download_id:
        raise DarwinException(f"Failed to register upload in {__name__}")

    signed_info = await async_create_signed_upload_url(api_client, team_slug, download_id)

    return signed_info


async def async_confirm_upload(api_client: ClientCore, team_slug: str, upload_id: str) -> JSONType:
    """
    Asynchronously confirm an upload/uploads was successful by ID

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to confirm the upload for
    upload_id: str
        The ID of the upload to confirm

    Returns
    -------
    JSONType
        The response from the API
    """
    return api_client.post(f"/api/v2/teams/{team_slug}/items/uploads/{upload_id}/confirm", data={})


def register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[Tuple[Item, Path], List[Tuple[Item, Path]]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> JSONType:
    """
    Asynchronously register an upload/uploads for a dataset that can then be used to upload files to Darwin

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to register the upload for
    dataset_slug: str
        The slug of the dataset to register the upload for
    items_and_paths: Union[Tuple[Item, Path], List[Tuple[Item, Path]]]
        A list of tuples, or a single tuple of Items and Paths to register for upload
    force_tiling: bool
        Whether to force tiling for the upload
    handle_as_slices: bool
        Whether to handle the upload as slices
    ignore_dicom_layout: bool
        Whether to ignore the dicom layout
    """
    # TODO: test me
    response = asyncio.run(
        async_register_upload(
            api_client, team_slug, dataset_slug, items_and_paths, force_tiling, handle_as_slices, ignore_dicom_layout
        )
    )
    return response


def create_signed_upload_url(
    api_client: ClientCore,
    upload_id: str,
    team_slug: str,
) -> JSONType:
    """
    Create a signed upload URL for an upload or uploads

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to register the upload for
    upload_id: str
        The ID of the upload to confirm

    Returns
    -------
    JSONType
        The response from the API
    """
    # TODO: test me
    return asyncio.run(async_create_signed_upload_url(api_client, upload_id, team_slug))


def register_and_create_signed_upload_url(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[List[Tuple[Item, Path]], Tuple[Item, Path]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> JSONType:
    """
    Register and create a signed upload URL for an upload or uploads

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to register the upload for
    dataset_slug: str
        The slug of the dataset to register the upload for

    Returns
    -------
    JSONType
        The response from the API
    """
    # TODO: test me
    return asyncio.run(
        async_register_and_create_signed_upload_url(
            api_client, team_slug, dataset_slug, items_and_paths, force_tiling, handle_as_slices, ignore_dicom_layout
        )
    )


def confirm_upload(api_client: ClientCore, team_slug: str, upload_id: str) -> JSONType:
    """
    Confirm an upload/uploads was successful by ID

    Parameters
    ----------
    api_client: ClientCore
        The client to use for the request
    team_slug: str
        The slug of the team to confirm the upload for
    upload_id: str
        The ID of the upload to confirm

    Returns
    -------
    JSONType
        The response from the API
    """
    # TODO: test me
    response = asyncio.run(async_confirm_upload(api_client, team_slug, upload_id))
    return response
