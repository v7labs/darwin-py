import unittest

import pytest
import responses
from pydantic import ValidationError

from darwin.future.core import backend as be
from darwin.future.core.client import Client
from darwin.future.data_objects.darwin_meta import Team
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
