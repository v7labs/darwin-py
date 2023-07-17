import unittest

import pytest
import responses
from pydantic import ValidationError

from darwin.future.core.client import Client
from darwin.future.data_objects.team import Team, TeamMember, get_team, get_team_members
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.fixtures import *


def test_get_team_returns_valid_team(base_client: Client, base_team_json: dict, base_team: Team) -> None:
    slug = "test-slug"
    endpoint = base_client.config.api_endpoint + f"teams/{slug}"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=base_team_json)

        team = get_team(base_client, slug)
        assert team == base_team


def test_get_team_fails_on_incorrect_input(base_client: Client, base_team: Team) -> None:
    slug = "test-slug"
    endpoint = base_client.config.api_endpoint + f"teams/{slug}"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json={})

        with pytest.raises(ValidationError):
            team = get_team(base_client, slug)


def test_get_team_members_returns_valid_list(base_client: Client, base_team_member_json: dict) -> None:
    synthetic_list = [TeamMember.parse_obj(base_team_member_json), TeamMember.parse_obj(base_team_member_json)]
    endpoint = base_client.config.api_endpoint + "memberships"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=[base_team_member_json, base_team_member_json])

        members, errors = get_team_members(base_client)
        assert len(members) == 2
        assert len(errors) == 0
        assert members == synthetic_list


def test_get_team_members_fails_on_incorrect_input(base_client: Client, base_team_member_json: dict) -> None:
    endpoint = base_client.config.api_endpoint + "memberships"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=[base_team_member_json, {}])

        members, errors = get_team_members(base_client)
        assert len(members) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], ValidationError)
        assert isinstance(members[0], TeamMember)


def test_team_from_client(base_client: Client, base_team_json: dict, base_team: Team) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            base_client.config.api_endpoint + f"teams/{base_client.config.default_team}",
            json=base_team_json,
        )

        team = Team.from_client(base_client)
        assert team == base_team
