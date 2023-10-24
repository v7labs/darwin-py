import asyncio
from logging import getLogger
from pathlib import Path
from typing import Dict, List, Tuple, Union

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import UploadItem
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import DarwinException

logger = getLogger(__name__)


async def _build_slots(item: UploadItem) -> List[Dict]:
    """
    (internal) Builds the slots for an item

    Parameters
    ----------
    item: UploadItem
        The item to build slots for

    Returns
    -------
    List[Dict]
        The built slots
    """

    if not item.slots:
        return []

    slots_to_return: List[Dict] = []

    for slot in item.slots:
        slot_dict: Dict[str, UnknownType] = {
            "slot_name": slot.slot_name,
            "file_name": slot.file_name,
            "fps": slot.fps,
        }

        if slot.storage_key is not None:
            slot_dict["storage_key"] = slot.storage_key

        if slot.as_frames is not None:
            slot_dict["as_frames"] = slot.as_frames

        if slot.extract_views is not None:
            slot_dict["extract_views"] = slot.extract_views

        if slot.metadata is not None:
            slot_dict["metadata"] = slot.metadata

        if slot.tags is not None:
            slot_dict["tags"] = slot.tags

        if slot.type is not None:
            slot_dict["type"] = slot.type

        slots_to_return.append(slot_dict)

    return slots_to_return


async def _build_layout(item: UploadItem) -> Dict:
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


async def _build_payload_items(
    items_and_paths: List[Tuple[UploadItem, Path]]
) -> List[Dict]:
    """
    Builds the payload for the items to be registered for upload

    Parameters
    ----------
    items_and_paths: List[Tuple[UploadItem, Path]]

    Returns
    -------
    List[Dict]
        The payload for the items to be registered for upload
    """

    return_list = []
    for item, path in items_and_paths:
        base_item = {
            "name": getattr(item, "name"),
            "slots": await _build_slots(item),
            "path": str(path),
        }

        if getattr(item, "tags", None):
            base_item["tags"] = item.tags

        if getattr(item, "layout", None):
            base_item["layout"] = await _build_layout(item)

        return_list.append(base_item)

    return return_list


async def async_register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[Tuple[UploadItem, Path], List[Tuple[UploadItem, Path]]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> Dict:
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
    items_and_paths: Union[Tuple[UploadItem, Path], List[Tuple[UploadItem, Path]]]
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
            (isinstance(item, UploadItem) and isinstance(path, Path))
            for item, path in items_and_paths
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

    try:
        response = api_client.post(
            f"/v2/teams/{team_slug}/items/register_upload", payload
        )
    except Exception as exc:
        logger.error(f"Failed to register upload in {__name__}", exc_info=exc)
        raise DarwinException(f"Failed to register upload in {__name__}") from exc

    assert isinstance(response, dict), "Unexpected return type from register upload"

    return response


async def async_create_signed_upload_url(
    api_client: ClientCore,
    team_slug: str,
    upload_id: str,
) -> str:
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
    try:
        response = api_client.get(
            f"/v2/teams/{team_slug}/items/uploads/{upload_id}/sign"
        )
    except Exception as exc:
        logger.error(f"Failed to create signed upload url in {__name__}", exc_info=exc)
        raise DarwinException(
            f"Failed to create signed upload url in {__name__}"
        ) from exc

    assert isinstance(
        response, dict
    ), "Unexpected return type from create signed upload url"

    if not response:
        logger.error(
            f"Failed to create signed upload url in {__name__}, got no response"
        )
        raise DarwinException(
            f"Failed to create signed upload url in {__name__}, got no response"
        )

    if "errors" in response:
        logger.error(
            f"Failed to create signed upload url in {__name__}, got errors: {response['errors']}"
        )
        raise DarwinException(f"Failed to create signed upload url in {__name__}")

    if "upload_url" not in response:
        logger.error(
            f"Failed to create signed upload url in {__name__}, got no upload_url"
        )
        raise DarwinException(
            f"Failed to create signed upload url in {__name__}, got no upload_url"
        )

    return response["upload_url"]


async def async_register_and_create_signed_upload_url(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[Tuple[UploadItem, Path], List[Tuple[UploadItem, Path]]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> List[Tuple[str, str]]:
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
    List[Tuple[str, str]]
        List of tuples of signed upload urls and upload ids
    """

    register = await async_register_upload(
        api_client,
        team_slug,
        dataset_slug,
        items_and_paths,
        force_tiling,
        handle_as_slices,
        ignore_dicom_layout,
    )

    if "errors" in register:
        raise DarwinException(f"Failed to register upload in {__name__}")

    if (
        "blocked_items" in register
        and isinstance(register["blocked_items"], list)
        and len(register["blocked_items"]) > 0
    ):
        raise DarwinException(
            f"Failed to register upload in {__name__}, got blocked items: {register['blocked_items']}"
        )

    assert "items" in register, "Unexpected return type from register upload"
    assert "blocked_items" in register, "Unexpected return type from register upload"

    uploaded_items = register["items"]

    upload_ids = []
    for item in uploaded_items:
        if "slots" in item:
            for slot in item["slots"]:
                if "upload_id" in slot:
                    upload_ids.append(slot["upload_id"])

    return [
        (await async_create_signed_upload_url(api_client, team_slug, id), id)
        for id in upload_ids
    ]


async def async_confirm_upload(
    api_client: ClientCore, team_slug: str, upload_id: str
) -> None:
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

    try:
        response = api_client.post(
            f"/v2/teams/{team_slug}/items/uploads/{upload_id}/confirm", data={}
        )
    except Exception as exc:
        logger.error(f"Failed to confirm upload in {__name__}", exc_info=exc)
        raise DarwinException(f"Failed to confirm upload in {__name__}") from exc

    assert isinstance(response, dict), "Unexpected return type from confirm upload"

    if "errors" in response:
        logger.error(
            f"Failed to confirm upload in {__name__}, got errors: {response['errors']}"
        )
        raise DarwinException(
            f"Failed to confirm upload in {__name__}: {str(response['errors'])}"
        )


def register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[Tuple[UploadItem, Path], List[Tuple[UploadItem, Path]]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> Dict:
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

    response = asyncio.run(
        async_register_upload(
            api_client,
            team_slug,
            dataset_slug,
            items_and_paths,
            force_tiling,
            handle_as_slices,
            ignore_dicom_layout,
        )
    )
    return response


def create_signed_upload_url(
    api_client: ClientCore,
    upload_id: str,
    team_slug: str,
) -> str:
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

    return asyncio.run(async_create_signed_upload_url(api_client, upload_id, team_slug))


def register_and_create_signed_upload_url(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items_and_paths: Union[List[Tuple[UploadItem, Path]], Tuple[UploadItem, Path]],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> List[Tuple[str, str]]:
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

    return asyncio.run(
        async_register_and_create_signed_upload_url(
            api_client,
            team_slug,
            dataset_slug,
            items_and_paths,
            force_tiling,
            handle_as_slices,
            ignore_dicom_layout,
        )
    )


def confirm_upload(api_client: ClientCore, team_slug: str, upload_id: str) -> None:
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
        None

    Raises
    ------
    DarwinException
        If the upload could not be confirmed
    """

    response = asyncio.run(async_confirm_upload(api_client, team_slug, upload_id))
    return response
