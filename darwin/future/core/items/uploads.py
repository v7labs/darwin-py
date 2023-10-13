import asyncio
from pathlib import Path
from typing import Dict, List, Tuple, Union

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.item import Item


def _build_payload_items(items_and_paths: List[Tuple[Item, Path]]) -> List[Dict]:
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

        return_list.append(base_item)

    return return_list


async def async_register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    items: Union[List[Item], Item],
    paths: Union[List[Path], Path],
    force_tiling: bool = False,
    handle_as_slices: bool = False,
    ignore_dicom_layout: bool = False,
) -> JSONType:
    if isinstance(items, Item):
        items = [items]
    if isinstance(paths, Path):
        paths = [paths]

    assert len(items) == len(paths), "items and paths must be the same length"

    items_and_paths = list(zip(items, paths))
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
) -> None:
    # TODO: implement
    raise NotImplementedError


async def async_register_and_create_signed_upload_url(api_client: ClientCore) -> None:
    # TODO: implement
    raise NotImplementedError


async def async_confirm_upload(api_client: ClientCore) -> None:
    # TODO: implement
    raise NotImplementedError


def register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    item: Item,
    path: Path,
) -> JSONType:
    response = asyncio.run(async_register_upload(api_client, team_slug, dataset_slug, item, path))
    return response


def create_signed_upload_url(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError


def register_and_create_signed_upload_url(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError


def confirm_upload(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError
