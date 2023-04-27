import pytest

from darwin.future.core.client import Client, DarwinConfig
from darwin.future.data_objects.darwin_meta import Team


@pytest.fixture
def base_config() -> DarwinConfig:
    return DarwinConfig(
        api_key="test_key",
        base_url="http://test_url.com/",
        api_endpoint="http://test_url.com/api/",
        default_team="default-team",
        teams={},
    )


@pytest.fixture
def base_client(base_config: DarwinConfig) -> Client:
    return Client(base_config)


@pytest.fixture
def base_team_json() -> dict:
    return {"slug": "test-team", "id": "0"}


@pytest.fixture
def base_team(base_team_json: dict) -> Team:
    return Team.parse_obj(base_team_json)
