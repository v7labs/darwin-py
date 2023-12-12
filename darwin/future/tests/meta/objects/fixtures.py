from typing import List
from uuid import UUID

from pytest import fixture

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.data_objects.item import ItemCore
from darwin.future.data_objects.team import TeamCore
from darwin.future.data_objects.workflow import WFStageCore, WorkflowCore
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.meta.objects.item import Item
from darwin.future.meta.objects.stage import Stage
from darwin.future.meta.objects.team import Team
from darwin.future.meta.objects.workflow import Workflow
from darwin.future.tests.core.fixtures import *


@fixture
def items(base_client: ClientCore, item_core_list: List[ItemCore]) -> List[Item]:
    return [
        Item(
            client=base_client,
            element=item,
            meta_params={"team_slug": "test", "dataset_id": 1},
        )
        for item in item_core_list
    ]


@fixture
def item(items: List[Item]) -> Item:
    return items[0]


@fixture
def base_UUID() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000000")


@fixture
def base_meta_team(base_client: ClientCore, base_team: TeamCore) -> Team:
    return Team(client=base_client, team=base_team)


@fixture
def base_meta_workflow(
    base_client: ClientCore, base_workflow: WorkflowCore
) -> Workflow:
    return Workflow(client=base_client, element=base_workflow)


@fixture
def workflow(base_client: ClientCore, base_workflow: WorkflowCore) -> Workflow:
    return Workflow(
        client=base_client,
        element=base_workflow,
        meta_params={"team_slug": "test", "dataset_id": 1, "workflow_id": 1},
    )


@fixture
def base_meta_stage(
    base_client: ClientCore, base_stage: WFStageCore, base_UUID: UUID
) -> Stage:
    return Stage(client=base_client, element=base_stage)


@fixture
def base_meta_stage_list(base_meta_stage: Stage, base_UUID: UUID) -> List[Stage]:
    return [base_meta_stage]


@fixture
def base_meta_dataset(base_client: ClientCore, base_dataset: DatasetCore) -> Dataset:
    return Dataset(
        client=base_client, element=base_dataset, meta_params={"team_slug": "test_team"}
    )


@fixture
def base_meta_item(base_client: ClientCore, base_item: ItemCore) -> Item:
    return Item(client=base_client, element=base_item)
