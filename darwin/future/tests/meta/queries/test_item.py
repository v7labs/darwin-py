from typing import List

import pytest
import responses
from responses.matchers import json_params_matcher, query_param_matcher

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import ItemLayout
from darwin.future.exceptions import BadRequest
from darwin.future.meta.objects.item import Item
from darwin.future.meta.queries.item import ItemQuery
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.meta.fixtures import *
from darwin.future.tests.meta.objects.fixtures import *


@pytest.fixture
def item_query(base_client: ClientCore) -> ItemQuery:
    return ItemQuery(
        client=base_client, meta_params={"team_slug": "test", "dataset_id": 1}
    )


def test_item_query_collect(item_query: ItemQuery, items_json: List[dict]) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        items = item_query.collect_all()
        assert len(items) == 5
        for i in range(5):
            assert items[i].name == f"item_{i}"


def test_delete(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        rsps.add(
            rsps.DELETE,
            items[0].client.config.api_endpoint + f"v2/teams/{team_slug}/items",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        }
                    }
                )
            ],
            json={},
        )
        item_query.delete()


def test_move_to_folder(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        path = "/new_folder"
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint + f"v2/teams/{team_slug}/items/path",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "path": path,
                    }
                )
            ],
            json={},
        )
        item_query.move_to_folder(path)


def test_move_to_folder_raises_on_incorrect_parameters(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        path = 1234
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint + f"v2/teams/{team_slug}/items/path",
            status=400,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "path": path,
                    }
                )
            ],
            json={},
        )
        with pytest.raises(BadRequest):
            item_query.move_to_folder(path)  # type: ignore


def test_set_priority(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        priority = 10
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint
            + f"v2/teams/{team_slug}/items/priority",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "priority": priority,
                    }
                )
            ],
            json={},
        )
        item_query.set_priority(priority)


def test_set_priority_raises_on_incorrect_parameters(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        priority = "10"
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint
            + f"v2/teams/{team_slug}/items/priority",
            status=400,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "priority": priority,
                    }
                )
            ],
            json={},
        )
        with pytest.raises(BadRequest):
            item_query.set_priority(priority)  # type: ignore


def test_restore(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint + f"v2/teams/{team_slug}/items/restore",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        }
                    }
                )
            ],
            json={},
        )
        item_query.restore()


def test_archive(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint + f"v2/teams/{team_slug}/items/archive",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        }
                    }
                )
            ],
            json={},
        )
        item_query.archive()


def test_set_layout(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        layout = ItemLayout(version=1, type="grid", slots=["slot1", "slot2"])
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint + f"v2/teams/{team_slug}/items/layout",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "layout": dict(layout),
                    }
                )
            ],
            json={},
        )
        item_query.set_layout(layout)


def test_set_layout_raises_on_incorrect_parameters(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock():
        items[0].meta_params["team_slug"]
        items[0].meta_params["dataset_id"]
        layout = "invalid_layout"
        with pytest.raises(AssertionError):
            item_query.set_layout(layout)  # type: ignore


def test_tag(item_query: ItemQuery, items_json: List[dict], items: List[Item]) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        tag_id = 123456
        rsps.add(
            rsps.POST,
            items[0].client.config.api_endpoint
            + f"v2/teams/{team_slug}/items/slots/tags",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "annotation_class_id": tag_id,
                    }
                )
            ],
            json={},
        )
        item_query.tag(tag_id)


def test_tag_bad_request(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock():
        tag_id = "123456"
        with pytest.raises(BadRequest) as excinfo:
            item_query.tag(tag_id)  # type: ignore
        (msg,) = excinfo.value.args
        assert msg == "tag_id must be an integer, got <class 'str'>"


def test_untag(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            item_query.client.config.api_endpoint + "v2/teams/test/items",
            match=[
                query_param_matcher(
                    {"page[offset]": "0", "page[size]": "500", "dataset_ids": "1"}
                )
            ],
            json={"items": items_json, "errors": []},
        )
        team_slug = items[0].meta_params["team_slug"]
        dataset_id = items[0].meta_params["dataset_id"]
        tag_id = 123456
        rsps.add(
            rsps.DELETE,
            items[0].client.config.api_endpoint
            + f"v2/teams/{team_slug}/items/slots/tags",
            status=200,
            match=[
                json_params_matcher(
                    {
                        "filters": {
                            "item_ids": [str(item.id) for item in items],
                            "dataset_ids": [dataset_id],
                        },
                        "annotation_class_id": tag_id,
                    }
                )
            ],
            json={},
        )
        item_query.untag(tag_id)


def test_untag_bad_request(
    item_query: ItemQuery, items_json: List[dict], items: List[Item]
) -> None:
    with responses.RequestsMock():
        tag_id = "123456"
        with pytest.raises(BadRequest) as excinfo:
            item_query.untag(tag_id)  # type: ignore
        (msg,) = excinfo.value.args
        assert msg == "tag_id must be an integer, got <class 'str'>"


def test_sort_method(base_client: ClientCore):
    item_query = ItemQuery(
        base_client, meta_params={"dataset_id": 0000, "team_slug": "test_team"}
    )

    item_query.sort(accuracy="desc", byte_size="asc")

    assert len(item_query.filters) == 2
    assert item_query.filters[0].name == "sort[accuracy]"
    assert item_query.filters[0].param == "desc"
