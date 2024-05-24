from typing import List

import pytest
import responses

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.meta.objects.team_member import TeamMember
from darwin.future.meta.queries.team_member import TeamMemberQuery
from darwin.future.tests.core.fixtures import *


def test_team_member_collects_basic(
    base_client: ClientCore, base_team_members_json: List[dict]
) -> None:
    query = TeamMemberQuery(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=base_team_members_json)
        members = query._collect()
        assert len(members) == len(TeamMemberRole)
        assert isinstance(members[0], TeamMember)


def test_team_member_only_passes_back_correct(
    base_client: ClientCore, base_team_member_json: dict
) -> None:
    query = TeamMemberQuery(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=[base_team_member_json, {}])
        members = query._collect()
        assert len(members) == 1
        assert isinstance(members[0], TeamMember)


@pytest.mark.parametrize("role", list(TeamMemberRole))
def test_team_member_filters_role(
    role: TeamMemberRole, base_client: ClientCore, base_team_members_json: List[dict]
) -> None:
    with responses.RequestsMock() as rsps:
        # Test equal
        query = TeamMemberQuery(base_client).where(
            {"name": "role", "param": role.value}
        )
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=base_team_members_json)
        members = query._collect()
        assert len(members) == 1
        assert members[0]._element.role == role

        # Test not equal
        rsps.reset()
        query = TeamMemberQuery(base_client).where(
            {"name": "role", "param": role.value, "modifier": "!="}
        )
        rsps.add(responses.GET, endpoint, json=base_team_members_json)
        members = query._collect()
        assert len(members) == len(TeamMemberRole) - 1
        for member in members.values():
            assert member._element.role != role


def test_team_member_filters_general(
    base_client: ClientCore, base_team_members_json: List[dict]
) -> None:
    for idx in range(len(base_team_members_json)):
        base_team_members_json[idx]["id"] = idx + 1

    with responses.RequestsMock() as rsps:
        query = TeamMemberQuery(base_client).where({"name": "id", "param": 1})
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=base_team_members_json)
        members = query._collect()
        assert len(members) == 1
        assert members[0]._element.id == 1

        # Test chained
        rsps.reset()

        rsps.add(responses.GET, endpoint, json=base_team_members_json)

        members = (
            TeamMemberQuery(base_client)
            .where({"name": "id", "param": 1, "modifier": ">"})
            .where(
                {"name": "id", "param": len(base_team_members_json), "modifier": "<"}
            )
            ._collect()
        )

        assert len(members) == len(base_team_members_json) - 2
