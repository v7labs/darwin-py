import asyncio
from pathlib import Path
from typing import List
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import Item


async def async_register_upload(
    api_client: ClientCore,
    team_slug: str,
    dataset_slug: str,
    item: Item,
    path: Path,
) -> None:
    """
        Payload example:
        {
      "dataset_slug": "my-dataset",
      "items": [
        {
          "layout": {
            "slots": [
              "1",
              "2",
              "3"
            ],
            "type": "grid",
            "version": 1
          },
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
              "tags": [
                "tag_class_name1",
                "tag_class_name2"
              ],
              "type": "image"
            }
          ],
          "tags": [
            "tag_class_name1",
            "tag_class_name2"
          ]
        },
        {
          "as_frames": false,
          "extract_views": false,
          "fps": "native",
          "metadata": {},
          "name": "some-item",
          "path": "/",
          "tags": [
            "tag_class_name1",
            "tag_class_name2"
          ],
          "type": "image"
        }
      ],
      "options": {
        "force_tiling": false,
        "handle_as_slices": false,
        "ignore_dicom_layout": false
      }
    }
    """
    # TODO: implement
    raise NotImplementedError


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


def register_upload(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError


def create_signed_upload_url(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError


def register_and_create_signed_upload_url(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError


def confirm_upload(api_client: ClientCore) -> None:
    # TODO: Implement
    raise NotImplementedError
