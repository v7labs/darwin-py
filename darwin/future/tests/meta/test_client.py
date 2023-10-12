import responses

from darwin.future.core.client import DarwinConfig
from darwin.future.data_objects.team import TeamCore
from darwin.future.meta.client import Client
from darwin.future.meta.objects.team import Team
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.meta.fixtures import *


def test_creates_from_api_key() -> None:
    with responses.RequestsMock() as rsps:
        base_api_endpoint = DarwinConfig._default_api_endpoint()
        rsps.add(
            responses.GET,
            base_api_endpoint + "users/token_info",
            json={"selected_team": {"slug": "test-team"}},
        )
        client = Client.from_api_key(api_key="test")
        assert client.config.default_team == "test-team"


def test_team_property(
    base_meta_client: Client, base_team: TeamCore, base_team_json: dict
) -> None:
    client = base_meta_client
    endpoint = client.config.api_endpoint + f"teams/{client.config.default_team}"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json=base_team_json)
        team = client.team
        assert isinstance(team, Team)
        assert team._element == base_team
