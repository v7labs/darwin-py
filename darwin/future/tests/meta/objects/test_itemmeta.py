from uuid import UUID

import pytest
import responses
from responses import json_params_matcher

from darwin.future.data_objects.item import ItemLayout, ItemSlot
from darwin.future.exceptions import BadRequest
from darwin.future.meta.objects.item import Item
from darwin.future.tests.meta.objects.fixtures import *


def test_item_properties(item: Item) -> None:
    assert isinstance(item.name, str)
    assert isinstance(item.id, UUID)
    assert isinstance(item.slots, list)
    for slot in item.slots:
        assert isinstance(slot, ItemSlot)
    assert isinstance(item.path, str)
    assert isinstance(item.dataset_id, int)
    assert isinstance(item.processing_status, str)
    assert isinstance(item.archived, (bool, type(None)))
    assert isinstance(item.priority, (int, type(None)))
    assert isinstance(item.tags, (list, dict, type(None)))
    assert isinstance(item.layout, (ItemLayout, type(None)))


def test_delete(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        rsps.add(
            rsps.DELETE,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        }
                    }
                )
            ],
            json={},
        )
        item.delete()


def test_move_to_folder(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        path = "/new_folder"
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/path",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "path": path,
                    }
                )
            ],
            json={},
        )
        item.move_to_folder(path)


def test_move_to_folder_raises_on_incorrect_parameters(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        path = 1234
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/path",
            status=400,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "path": path,
                    }
                )
            ],
            json={},
        )
        with pytest.raises(BadRequest):
            item.move_to_folder(path)
