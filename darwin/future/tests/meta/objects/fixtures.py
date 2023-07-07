from typing import List
from uuid import UUID

from pytest import fixture, raises

from darwin.future.core.client import Client
from darwin.future.data_objects.team import Team
from darwin.future.data_objects.workflow import WFStage, Workflow
from darwin.future.meta.objects import stage
from darwin.future.meta.objects.stage import StageMeta
from darwin.future.meta.objects.team import TeamMeta
from darwin.future.meta.objects.workflow import WorkflowMeta
from darwin.future.tests.core.fixtures import *


@fixture
def base_UUID() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000000")


@fixture
def base_meta_team(base_client: Client, base_team: Team) -> TeamMeta:
    return TeamMeta(base_client, base_team)


@fixture
def base_meta_workflow(base_client: Client, base_workflow: Workflow) -> WorkflowMeta:
    return WorkflowMeta(base_client, base_workflow)


@fixture
def base_meta_stage(base_client: Client, base_stage: WFStage, base_UUID: UUID) -> StageMeta:
    return StageMeta(base_client, base_stage, base_UUID)


@fixture
def base_meta_stage_list(base_meta_stage: StageMeta, base_UUID: UUID) -> List[StageMeta]:
    return [base_meta_stage]
