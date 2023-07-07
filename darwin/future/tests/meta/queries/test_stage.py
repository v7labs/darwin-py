import json
from typing import List

import pytest
import responses
from sklearn import base

from darwin.future.core.client import Client
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.data_objects.workflow import WFStage, Workflow
from darwin.future.meta.objects.stage import StageMeta
from darwin.future.meta.objects.workflow import WorkflowMeta
from darwin.future.meta.queries.stage import StageQuery
from darwin.future.tests.core.fixtures import *


@pytest.fixture
def filled_query(base_client: Client, base_workflow_meta: WorkflowMeta) -> StageQuery:
    return StageQuery(base_client, meta_params={"workflow_id": str(base_workflow_meta.id)})


@pytest.fixture
def base_workflow_meta(base_client: Client, base_single_workflow_object: dict) -> WorkflowMeta:
    return WorkflowMeta(base_client, Workflow.parse_obj(base_single_workflow_object))


def test_stage_collects_basic(
    filled_query: StageQuery, base_single_workflow_object: dict, base_workflow_meta: WorkflowMeta
) -> None:
    UUID = base_workflow_meta.id
    with responses.RequestsMock() as rsps:
        endpoint = filled_query.client.config.api_endpoint + f"v2/teams/default-team/workflows/{UUID}"
        rsps.add(responses.GET, endpoint, json=base_single_workflow_object)
        stages = filled_query.collect()
        assert len(stages) == len(base_workflow_meta.stages)
        assert isinstance(stages[0], StageMeta)


# def test_team_member_only_passes_back_correct(base_client: Client, base_team_member_json: dict) -> None:
#     query = StageQuery(base_client)
#     with responses.RequestsMock() as rsps:
#         endpoint = base_client.config.api_endpoint + "memberships"
#         rsps.add(responses.GET, endpoint, json=[base_team_member_json, {}])
#         members = query.collect()
#         assert len(members) == 1
#         assert isinstance(members[0], TeamMemberMeta)


# @pytest.mark.parametrize("role", [role for role in TeamMemberRole])
# def test_team_member_filters_role(
#     role: TeamMemberRole, base_client: Client, base_team_members_json: List[dict]
# ) -> None:
#     with responses.RequestsMock() as rsps:
#         # Test equal
#         query = TeamMemberQuery(base_client).where({"name": "role", "param": role.value})
#         endpoint = base_client.config.api_endpoint + "memberships"
#         rsps.add(responses.GET, endpoint, json=base_team_members_json)
#         members = query.collect()
#         assert len(members) == 1
#         assert members[0]._item is not None
#         assert members[0]._item.role == role

#         # Test not equal
#         rsps.reset()
#         query = TeamMemberQuery(base_client).where({"name": "role", "param": role.value, "modifier": "!="})
#         rsps.add(responses.GET, endpoint, json=base_team_members_json)
#         members = query.collect()
#         assert len(members) == len(TeamMemberRole) - 1
#         for member in members:
#             assert member._item is not None
#             assert member._item.role != role


# def test_team_member_filters_general(base_client: Client, base_team_members_json: List[dict]) -> None:
#     for idx in range(len(base_team_members_json)):
#         base_team_members_json[idx]["id"] = idx + 1

#     with responses.RequestsMock() as rsps:
#         query = TeamMemberQuery(base_client).where({"name": "id", "param": 1})
#         endpoint = base_client.config.api_endpoint + "memberships"
#         rsps.add(responses.GET, endpoint, json=base_team_members_json)
#         members = query.collect()
#         assert len(members) == 1
#         assert members[0]._item is not None
#         assert members[0]._item.id == 1

#         # Test chained
#         rsps.reset()

#         rsps.add(responses.GET, endpoint, json=base_team_members_json)

#         members = (
#             TeamMemberQuery(base_client)
#             .where({"name": "id", "param": 1, "modifier": ">"})
#             .where({"name": "id", "param": len(base_team_members_json), "modifier": "<"})
#             .collect()
#         )

#         assert len(members) == len(base_team_members_json) - 2
