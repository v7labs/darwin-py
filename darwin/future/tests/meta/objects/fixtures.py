from typing import List
from uuid import UUID

from pytest import fixture, raises

from darwin.future.core.client import CoreClient
from darwin.future.data_objects.team import TeamCore
from darwin.future.data_objects.workflow import WFStageCore, WorkflowCore
from darwin.future.meta.objects import stage
from darwin.future.meta.objects.stage import Stage
from darwin.future.meta.objects.team import Team
from darwin.future.meta.objects.workflow import Workflow
from darwin.future.tests.core.fixtures import *


@fixture
def base_UUID() -> UUID:
    return UUID("00000000-0000-0000-0000-000000000000")


@fixture
def base_meta_team(base_client: CoreClient, base_team: TeamCore) -> Team:
    return Team(base_client, base_team)


@fixture
def base_meta_workflow(base_client: CoreClient, base_workflow: WorkflowCore) -> Workflow:
    return Workflow(base_client, base_workflow)


@fixture
def base_meta_stage(base_client: CoreClient, base_stage: WFStageCore, base_UUID: UUID) -> Stage:
    return Stage(base_client, base_stage, base_UUID)


@fixture
def base_meta_stage_list(base_meta_stage: Stage, base_UUID: UUID) -> List[Stage]:
    return [base_meta_stage]
