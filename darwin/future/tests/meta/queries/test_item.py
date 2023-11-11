from typing import List
from uuid import uuid4

import pytest
import responses
from responses.matchers import query_param_matcher

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import ItemCore, ItemLayout, ItemSlot
from darwin.future.meta.objects.item import Item
from darwin.future.meta.queries.item import ItemQuery
from darwin.future.tests.core.fixtures import *


@pytest.fixture
def item_core_list() -> List[ItemCore]:
    items = []
    for i in range(5):
        slot = ItemSlot(slot_name=f"slot_{i}", file_name=f"file_{i}.jpg")
        layout = ItemLayout(slots=[f"slot_{i}"], type="grid", version=1)
        item = ItemCore(
            name=f"item_{i}",
            id=uuid4(),
            slots=[slot],
            dataset_id=i,
            processing_status="processed",
            layout=layout,
        )
        items.append(item)
    return items


@pytest.fixture
def items(base_client: ClientCore, item_list: List[ItemCore]) -> List[Item]:
    return [
        Item(
            client=base_client,
            element=item,
            meta_params={"team_slug": "test", "dataset_id": 1},
        )
        for item in item_list
    ]


@pytest.fixture
def items_json(item_core_list: List[ItemCore]) -> List[dict]:
    items: List[dict] = []
    for item in item_core_list:
        temp = dict(item)
        temp["id"] = str(temp["id"])
        temp["slots"] = [dict(slot) for slot in temp["slots"]]
        temp["layout"] = dict(temp["layout"])
        items.append(temp)
    return items


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
