from typing import List
from uuid import UUID

import responses
from pytest import fixture, mark, raises
from responses import RequestsMock
from sklearn import base

from darwin.future.core.client import DarwinConfig
from darwin.future.data_objects.workflow import WFStageCore, WFTypeCore
from darwin.future.meta.client import Client
from darwin.future.meta.objects.stage import Stage
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.core.items.fixtures import *
from darwin.future.tests.meta.fixtures import *


@fixture
def uuid_str() -> str:
    return "00000000-0000-0000-0000-000000000000"


@fixture
def base_WFStage(uuid_str: str) -> WFStageCore:
    return WFStageCore(id=UUID(uuid_str), name="test-stage", type=WFTypeCore.ANNOTATE, assignable_users=[], edges=[])


@fixture
def stage_meta(base_meta_client: Client, base_WFStage: WFStageCore, workflow_id: UUID) -> Stage:
    return Stage(
        base_meta_client, base_WFStage, {"team_slug": "default-team", "dataset_id": 1337, "workflow_id": workflow_id}
    )


def test_item_ids(base_meta_client: Client, stage_meta: Stage, UUIDs_str: List[str], UUIDs: List[UUID]) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_meta_client.config.api_endpoint
            + f"v2/teams/default-team/items/ids?workflow_stage_ids={str(stage_meta.id)}&dataset_ids=1337",
            json={"item_ids": UUIDs_str},
            status=200,
        )
        item_ids = stage_meta.item_ids
        assert item_ids == UUIDs


def test_move_attached_files_to_stage(
    base_meta_client: Client, stage_meta: Stage, UUIDs_str: List[str], UUIDs: List[UUID]
) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_meta_client.config.api_endpoint
            + f"v2/teams/default-team/items/ids?workflow_stage_ids={str(stage_meta.id)}&dataset_ids=1337",
            json={"item_ids": UUIDs_str},
            status=200,
        )
        rsps.add(
            rsps.POST,
            base_meta_client.config.api_endpoint + "v2/teams/default-team/items/stage",
            json={"success": UUIDs_str},
            status=200,
        )
        stage_meta.move_attached_files_to_stage(stage_meta.id)
        assert rsps.assert_call_count(base_meta_client.config.api_endpoint + "v2/teams/default-team/items/stage", 1)
        assert rsps.assert_call_count(
            base_meta_client.config.api_endpoint
            + f"v2/teams/default-team/items/ids?workflow_stage_ids={str(stage_meta.id)}&dataset_ids=1337",
            1,
        )
