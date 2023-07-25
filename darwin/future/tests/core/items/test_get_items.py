from typing import List
from uuid import UUID, uuid4

import responses

from darwin.future.core.client import Client
from darwin.future.core.items.get import get_item_ids, get_item_ids_stage
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.core.items.fixtures import *


def test_get_item_ids(UUIDs: List[UUID], UUIDs_str: List[str], base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + f"v2/teams/default-team/items/ids?not_statuses=archived,error&sort[id]=desc&dataset_ids=1337",
            json={"item_ids": UUIDs_str},
            status=200,
        )
        item_ids = get_item_ids(base_client, "default-team", "1337")
        assert item_ids == UUIDs

def test_get_item_ids_stage(UUIDs: List[UUID], UUIDs_str: List[str], base_client: Client) -> None:
    stage_id = str(uuid4())
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + f"v2/teams/default-team/items/ids?workflow_stage_ids={stage_id}&dataset_ids=1337",
            json={"item_ids": UUIDs_str},
            status=200,
        )
        item_ids = get_item_ids_stage(base_client, "default-team", "1337", stage_id)
        assert item_ids == UUIDs
