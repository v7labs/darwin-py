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


def test_delete_with_bad_team_slug(item: Item) -> None:
    with pytest.raises(AssertionError):
        item.meta_params["team_slug"] = 123
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


def test_move_to_folder_with_bad_team_slug(item: Item) -> None:
    with pytest.raises(AssertionError):
        path = "/new_folder"
        item.meta_params["team_slug"] = 123
        item.move_to_folder(path)


def test_set_priority(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        priority = 10
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/priority",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "priority": priority,
                    }
                )
            ],
            json={},
        )
        item.set_priority(priority)


def test_set_priority_raises_on_incorrect_parameters(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        priority = "10"
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/priority",
            status=400,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "priority": priority,
                    }
                )
            ],
            json={},
        )
        with pytest.raises(BadRequest):
            item.set_priority(priority)


def test_set_priority_with_bad_team_slug(item: Item) -> None:
    with pytest.raises(AssertionError):
        priority = 10
        item.meta_params["team_slug"] = 123
        item.set_priority(priority)


def test_restore(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/restore",
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
        item.restore()


def test_restore_with_bad_team_slug(item: Item) -> None:
    with pytest.raises(AssertionError):
        item.meta_params["team_slug"] = 123
        item.restore()


def test_archive(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/archive",
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
        item.archive()


def test_archive_with_bad_team_slug(item: Item) -> None:
    with pytest.raises(AssertionError):
        item.meta_params["team_slug"] = 123
        item.archive()
