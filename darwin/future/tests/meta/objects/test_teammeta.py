from unittest.mock import Mock, patch

import responses
from pytest import fixture, raises

from darwin.future.core.client import DarwinConfig
from darwin.future.meta.client import MetaClient
from darwin.future.meta.objects.team import TeamMeta
from darwin.future.tests.core.fixtures import *


def test_team_meta_collects_basic(base_client: Client, base_teams_json: dict) -> None:
    query = TeamMeta(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "teams"
        rsps.add(responses.GET, endpoint, json=base_teams_json)
        teams = query.collect()

        assert len(teams) == 2
        assert all([isinstance(team, Team) for team in teams])