import unittest

import pytest
import responses
from pydantic import ValidationError

from darwin.future.core import backend as be
from darwin.future.core.client import Client
from darwin.future.data_objects.team import Team, TeamMember
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.fixtures import *


def test_get_team_returns_valid_team(base_client: Client, base_team_json: dict, base_team: Team) -> None:
    slug = "test-slug"
    endpoint = base_client.config.api_endpoint + f"teams/{slug}"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=base_team_json)

        team = be.get_team(base_client, slug)
        assert team == base_team


def test_get_team_fails_on_incorrect_input(base_client: Client, base_team: Team) -> None:
    slug = "test-slug"
    endpoint = base_client.config.api_endpoint + f"teams/{slug}"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json={})

        with pytest.raises(ValidationError):
            team = be.get_team(base_client, slug)


def test_get_team_members_returns_valid_list(base_client: Client, base_team_member_json: dict) -> None:
    synthetic_list = [TeamMember.parse_obj(base_team_member_json), TeamMember.parse_obj(base_team_member_json)]
    endpoint = base_client.config.api_endpoint + "memberships"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=[base_team_member_json, base_team_member_json])

        members, errors = be.get_team_members(base_client)
        assert len(members) == 2
        assert len(errors) == 0
        assert members == synthetic_list


def test_get_team_members_fails_on_incorrect_input(base_client: Client, base_team_member_json: dict) -> None:
    endpoint = base_client.config.api_endpoint + "memberships"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=[base_team_member_json, {}])

        members, errors = be.get_team_members(base_client)
        assert len(members) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], ValidationError)
        assert isinstance(members[0], TeamMember)
