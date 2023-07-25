from typing import Dict, List
from uuid import UUID, uuid4

import pytest
import responses

from darwin.future.core.client import Client
from darwin.future.core.items.move_items import move_items_to_stage
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.core.items.fixtures import *


@pytest.fixture
def move_payload(UUIDs_str: List[str], stage_id: UUID, workflow_id: UUID) -> Dict:
    return {
            "filters": {
                "dataset_ids": [1337],
                "item_ids": UUIDs_str,
            },
            "stage_id": str(stage_id),
            "workflow_id": str(workflow_id),
        }
    
def test_move_items(base_client: Client, move_payload: Dict, stage_id: UUID, workflow_id: UUID, UUIDs_str: List[str], UUIDs: List[UUID]) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            base_client.config.api_endpoint + "v2/teams/default-team/items/stage",
            json={"success": UUIDs_str}, 
            status=200,
        )
        item_ids = move_items_to_stage(base_client, "default-team", workflow_id, 1337, stage_id, UUIDs)
        assert rsps.assert_call_count(base_client.config.api_endpoint + "v2/teams/default-team/items/stage", 1)