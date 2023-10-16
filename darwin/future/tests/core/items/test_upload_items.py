import asyncio
from typing import Coroutine, List
from unittest.mock import MagicMock, patch

import pytest
import responses

import darwin.future.core.items.uploads as uploads
from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import Item
from darwin.future.meta.objects import base
from darwin.future.tests.core.fixtures import *  # noqa: F401,F403

from .fixtures import *  # noqa: F401,F403


class TestRegisterUpload:
    @pytest.fixture
    def default_url(self, base_client: ClientCore) -> str:
        return f"{base_client.config.base_url}api/v2/teams/{base_client.config.default_team}/items"

    @responses.activate()
    @patch.object(uploads, "_build_payload_items")
    def test_async_register_uploads_accepts_tuple_or_list_of_tuples(  # type: ignore
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
