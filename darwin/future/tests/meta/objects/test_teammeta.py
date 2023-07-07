from unittest.mock import Mock, patch

import responses
from pytest import fixture, raises

from darwin.future.core.client import Client, DarwinConfig
from darwin.future.data_objects.team import Team, TeamMember
from darwin.future.meta.objects.team import TeamMeta
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.meta.objects.fixtures import *


def test_team_meta_collects_members(
    base_meta_team: TeamMeta, base_client: Client, base_team_member: TeamMember, base_team_member_json: dict
) -> None:
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "memberships"
        rsps.add(responses.GET, endpoint, json=[base_team_member_json])
        members = base_meta_team.members.collect()
        assert len(members) == 1
        assert members[0]._item == base_team_member
