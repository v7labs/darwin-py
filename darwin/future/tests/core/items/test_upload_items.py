import asyncio
from pathlib import Path
from typing import Coroutine, Dict, List, Tuple
from unittest.mock import MagicMock, patch

import pytest
import responses

import darwin.future.core.items.uploads as uploads
from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import Item, ItemSlot
from darwin.future.tests.core.fixtures import *  # noqa: F401,F403

from .fixtures import *  # noqa: F401,F403


class TestBuildSlots:
    BUILD_SLOT_RETURN_TYPE = List[Dict]

    items_and_expectations: List[Tuple[Item, BUILD_SLOT_RETURN_TYPE]] = []

    # Test empty slots
    items_and_expectations.append((Item(name="name_with_no_slots", slots=[]), []))

    # Test Simple slot with no non-required fields
    items_and_expectations.append(
        (
            Item(
                name="name_with_simple_slot",
                slots=[
                    ItemSlot(
                        slot_name="slot_name_simple",
                        file_name="file_name",
                        storage_key="storage_key",
                    )
                ],
            ),
            [
                {
                    "slot_name": "slot_name_simple",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "type": "image",
                    "fps": 0,
                }
            ],
        )
    )

    # Test with multiple slots
    items_and_expectations.append(
        (
            Item(
                name="name_with_multiple_slots",
                slots=[
                    ItemSlot(
                        slot_name="slot_name1",
                        file_name="file_name1",
                        storage_key="storage_key1",
                    ),
                    ItemSlot(
                        slot_name="slot_name2",
                        file_name="file_name2",
                        storage_key="storage_key2",
                    ),
                ],
            ),
            [
                {
                    "slot_name": "slot_name1",
                    "file_name": "file_name1",
                    "storage_key": "storage_key1",
                    "type": "image",
                    "fps": 0,
                },
                {
                    "slot_name": "slot_name2",
                    "file_name": "file_name2",
                    "storage_key": "storage_key2",
                    "type": "image",
                    "fps": 0,
                },
            ],
        )
    )

    # Test with `as_frames` optional field
    items_and_expectations.append(
        (
            Item(
                name="name_testing_as_frames",
                slots=[
                    ItemSlot(
                        slot_name="slot_name1",
                        file_name="file_name",
                        storage_key="storage_key",
                        as_frames=True,
                    ),
                    ItemSlot(
                        slot_name="slot_name2",
                        file_name="file_name",
                        storage_key="storage_key",
                        as_frames=False,
                    ),
                    ItemSlot(
                        slot_name="slot_name3",
                        file_name="file_name",
                        storage_key="storage_key",
                    ),
                ],
            ),
            [
                {
                    "slot_name": "slot_name1",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                    "as_frames": True,
                },
                {
                    "slot_name": "slot_name2",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                    "as_frames": False,
                },
                {
                    "slot_name": "slot_name3",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                },
            ],
        )
    )

    # Test with `extract_views` optional field
    items_and_expectations.append(
        (
            Item(
                name="name_testing_extract_views",
                slots=[
                    ItemSlot(
                        slot_name="slot_name1",
                        file_name="file_name",
                        storage_key="storage_key",
                        extract_views=True,
                    ),
                    ItemSlot(
                        slot_name="slot_name2",
                        file_name="file_name",
                        storage_key="storage_key",
                        extract_views=False,
                    ),
                    ItemSlot(
                        slot_name="slot_name3",
                        file_name="file_name",
                        storage_key="storage_key",
                    ),
                ],
            ),
            [
                {
                    "slot_name": "slot_name1",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                    "extract_views": True,
                },
                {
                    "slot_name": "slot_name2",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                    "extract_views": False,
                },
                {
                    "slot_name": "slot_name3",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                },
            ],
        )
    )

    # Test with `fps` semi-optional field - field defaults to 0 if not provided
    items_and_expectations.append(
        (
            Item(
                name="name_with_simple_slot",
                slots=[
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                        fps=25,  # Testing int
                    ),
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                        # FIXME: this should pass through as a float but doesn't
                        fps=float(29.997),  # Testing float
                    ),
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                        fps="native",  # Testing literal
                    ),
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                    ),
                ],
            ),
            [
                {
                    "slot_name": "slot_name25",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "type": "image",
                    "fps": 25,
                },
                {
                    "slot_name": "slot_name29.997",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "type": "image",
                    "fps": 29.997,
                },
                {
                    "slot_name": "slot_namenative",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "type": "image",
                    "fps": "native",
                },
                {
                    "slot_name": "slot_name",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "type": "image",
                    "fps": 0,
                },
            ],
        )
    )

    # Test with `metadata` optional field
    items_and_expectations.append(
        (
            Item(
                name="name_with_simple_slot",
                slots=[
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                        metadata={"key": "value"},
                    ),
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                        metadata=None,
                    ),
                    ItemSlot(
                        slot_name="slot_name",
                        file_name="file_name",
                        storage_key="storage_key",
                    ),
                ],
            ),
            [
                {
                    "slot_name": "slot_name",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                    "metadata": {"key": "value"},
                },
                {
                    "slot_name": "slot_name",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                },
                {
                    "slot_name": "slot_name",
                    "file_name": "file_name",
                    "storage_key": "storage_key",
                    "fps": 0,
                    "type": "image",
                },
            ],
        )
    )

    @pytest.mark.parametrize("item,expected", [(item, expected) for item, expected in items_and_expectations])
    def test_build_slots(self, item: Item, expected: List[Dict]) -> None:
        result = asyncio.run(uploads._build_slots(item))
        assert result == expected


class TestRegisterUpload:
    @pytest.fixture
    def default_url(self, base_client: ClientCore) -> str:
        return f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/items"

    @responses.activate()
    @patch.object(uploads, "_build_payload_items")
    def test_async_register_uploads_accepts_tuple_or_list_of_tuples(
        self,
        mock_build_payload_items: MagicMock,
        base_client: ClientCore,
        default_url: str,
    ) -> None:
        mock_build_payload_items.return_value = []

        item = Item(name="name", path="path", slots=[])

        item_and_path = (item, Path("path"))
        items_and_paths = [item_and_path]

        responses.add(
            "post",
            f"{default_url}/register_upload",
            status=200,
            json={
                "dataset_slug": "dataset_slug",
                "items": [],
                "options": {"force_tiling": False, "handle_as_slices": False, "ignore_dicom_layout": False},
            },
        )

        responses.add(
            "post",
            f"{default_url}/register_upload",
            status=200,
            json={
                "dataset_slug": "dataset_slug",
                "items": [],
                "options": {"force_tiling": False, "handle_as_slices": False, "ignore_dicom_layout": False},
            },
        )

        tasks: List[Coroutine] = [
            uploads.async_register_upload(
                base_client,
                "team_slug",
                "dataset_slug",
                items_and_paths,
            ),
            uploads.async_register_upload(
                base_client,
                "team_slug",
                "dataset_slug",
                item_and_path,
            ),
        ]
        try:
            outputs = asyncio.run(tasks[0]), asyncio.run(tasks[1])
        except Exception as e:
            print(e)
            pytest.fail()

        print(outputs)


class TestCreateSignedUploadUrl:
    ...


class TestRegisterAndCreateSignedUploadUrl:
    ...


class TestConfirmUpload:
    ...


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
