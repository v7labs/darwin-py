import asyncio
from concurrent.futures import Future
from pathlib import Path
from typing import Coroutine, Dict, List, Tuple, Union
from urllib import response

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.item import Item, ItemSlot
from darwin.future.exceptions import DarwinException

"""
    [
        {
            "layout": {"slots": ["1", "2", "3"], "type": "grid", "version": 1},
            "name": "some-item",
            "path": "/",
            "slots": [
                {
                    "as_frames": false,
                    "extract_views": false,
                    "file_name": "my_image.jpg",
                    "fps": "native",
                    "metadata": {},
                    "slot_name": "0",
                    "tags": ["tag_class_name1", "tag_class_name2"],
                    "type": "image",
                }
            ],
            "tags": ["tag_class_name1", "tag_class_name2"],
        },
        {
            "as_frames": false,
            "extract_views": false,
            "fps": "native",
            "metadata": {},
            "name": "some-item",
            "path": "/",
            "tags": ["tag_class_name1", "tag_class_name2"],
            "type": "image",
        },
    ]
"""

def _build_slots(slots: List[ItemSlot]) -> List[Dict]:
    # TODO: implememnt me
    return NotImplemented


def _build_layout(layout: Dict) -> Dict:
    # TODO: implement me
    return NotImplemented

def _build_payload_items(items_and_paths: List[Tuple[Item, Path]]) -> List[Dict]:
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
    # TODO: test me
    return_list = []
    for item, path in items_and_paths:
        base_item = {
            "name": getattr(item, "name"),
            "path:": str(path),
            "tags": getattr(item, "tags", []),
        }

        # TODO: Handle slots - not sure how well the Item reflects the needed payload
        # It's complex if the item passed is DatasetsV2.ItemRegistration.NewCompositeItem
        # and simpler if it's DatasetsV2.ItemRegistration.NewSimpleItem
        # TODO: Handle layout

        if getattr(item, "slots", None):
            base_item["slots"] = _build_slots(item)

        if getattr(item, "layout", None):
        base_item["layout"] = _build_layout(item) #! FIXME: Type bug here

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

    payload_items = _build_payload_items(items_and_paths)

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
) -> Coroutine[Future, None, JSONType]:
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

    return async_create_signed_upload_url(api_client, team_slug, download_id)


async def async_confirm_upload(api_client: ClientCore, team_slug: str, upload_id: str) -> JSONType
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
    # TODO: test me
    response = asyncio.run(async_register_upload(api_client, team_slug, dataset_slug, items_and_paths, force_tiling, handle_as_slices, ignore_dicom_layout))
    return response


def create_signed_upload_url(
    api_client: ClientCore,
    upload_id: str,
    team_slug: str,
) -> JSONType:
    # TODO: test me
    return asyncio.run(async_create_signed_upload_url(api_client, upload_id, team_slug))


def register_and_create_signed_upload_url(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    item: Item,
    path: Path
) -> None:
    #TODO: test me
    return asyncio.run(
        # ! FIXME: Type bug here
        async_register_and_create_signed_upload_url(
            api_client,
            team_slug,
            dataset_slug,
            item,
            path
        )
    )


def confirm_upload(api_client: ClientCore, team_slug: str, upload_id: str) -> JSONType:
    # TODO: test me
    response = asyncio.run(async_confirm_upload(api_client, team_slug, upload_id))
    return response
