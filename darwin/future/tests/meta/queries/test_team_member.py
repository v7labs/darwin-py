import unittest
from typing import List

import pytest
import responses

from darwin.future.core.client import Client
from darwin.future.data_objects.darwin_meta import TeamMember, TeamMemberRole
from darwin.future.meta.queries.team_member import TeamMemberQuery
from darwin.future.tests.core.fixtures import *


def test_team_member_collects_basic(base_client: Client, base_team_members_json: List[dict]) -> None:
    query = TeamMemberQuery()
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=base_team_members_json)
        members = query.collect(base_client)
        assert len(members) == len(TeamMemberRole)
        assert isinstance(members[0], TeamMember)


def test_team_member_only_passes_back_correct(base_client: Client, base_team_member_json: dict) -> None:
    query = TeamMemberQuery()
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=[base_team_member_json, {}])
        members = query.collect(base_client)
        assert len(members) == 1
        assert isinstance(members[0], TeamMember)


@pytest.mark.parametrize("role", [role for role in TeamMemberRole])
def test_team_member_filters_role(
    role: TeamMemberRole, base_client: Client, base_team_members_json: List[dict]
) -> None:
    query = TeamMemberQuery().where({"name": "role", "value": role.value})
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=base_team_members_json)
        members = query.collect(base_client)
        assert len(members) == 1
        assert members[0].role == role
