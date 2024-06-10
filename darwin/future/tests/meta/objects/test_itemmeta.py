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
            item.move_to_folder(path)  # type: ignore


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
            item.set_priority(priority)  # type: ignore


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


def test_set_layout(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        layout = ItemLayout(version=1, type="grid", slots=["slot1", "slot2"])
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/layout",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "layout": layout.model_dump(),
                    }
                )
            ],
            json={},
        )
        item.set_layout(layout)


def test_set_layout_raises_on_incorrect_parameters(item: Item) -> None:
    with responses.RequestsMock():
        item.meta_params["team_slug"]
        item.meta_params["dataset_id"]
        layout = "invalid_layout"
        with pytest.raises(AssertionError):
            item.set_layout(layout)  # type: ignore


def test_set_layout_with_bad_team_slug(item: Item) -> None:
    with pytest.raises(AssertionError):
        layout = ItemLayout(version=1, type="grid", slots=["slot1", "slot2"])
        item.meta_params["team_slug"] = 123
        item.set_layout(layout)


def test_tag(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        tag_id = 123456
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/slots/tags",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "annotation_class_id": tag_id,
                    }
                )
            ],
            json={},
        )
        item.tag(tag_id)


def test_tag_bad_input(item: Item) -> None:
    with responses.RequestsMock():
        tag_id = "123456"
        with pytest.raises(BadRequest) as excinfo:
            item.tag(tag_id)  # type: ignore
        (msg,) = excinfo.value.args
        assert msg == "tag_id must be an integer, got <class 'str'>"


def test_untag(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        tag_id = 123456
        rsps.add(
            rsps.DELETE,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/slots/tags",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "annotation_class_id": tag_id,
                    }
                )
            ],
            json={},
        )
        item.untag(tag_id)


def test_untag_bad_input(item: Item) -> None:
    with responses.RequestsMock():
        tag_id = "123456"
        with pytest.raises(BadRequest) as excinfo:
            item.untag(tag_id)  # type: ignore
        (msg,) = excinfo.value.args
        assert msg == "tag_id must be an integer, got <class 'str'>"


def test_set_stage(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        stage_id = "123456"
        workflow_id = "123456"
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/stage",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "stage_id": stage_id,
                        "workflow_id": workflow_id,
                    }
                )
            ],
            json={},
        )
        item.set_stage(stage_id, workflow_id)


def test_assign(item: Item) -> None:
    with responses.RequestsMock() as rsps:
        team_slug = item.meta_params["team_slug"]
        dataset_id = item.meta_params["dataset_id"]
        assignee_id = 123456
        workflow_id = "123456"
        rsps.add(
            rsps.POST,
            item.client.config.api_endpoint + f"v2/teams/{team_slug}/items/assign",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id)],
                            "dataset_ids": [dataset_id],
                        },
                        "assignee_id": assignee_id,
                        "workflow_id": workflow_id,
                    }
                )
            ],
            json={},
        )
        item.assign(assignee_id, workflow_id)
