import logging
from pathlib import Path

import responses

from darwin.client import Client
from darwin.config import Config
from darwin.datatypes import Feature


def describe_get_team_features():
    @responses.activate
    def it_returns_list_of_features():
        team_slug: str = "team-slug"
        darwin_datasets_path: Path = Path.home() / ".darwin" / "datasets"

        config = Config()
        config.put(["global", "api_endpoint"], "http://localhost/api")
        config.put(["global", "base_url"], "http://localhost")
        config.put(["teams", team_slug, "api_key"], "mock_api_key")
        config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
        client = Client(config, logging.getLogger())

        api: str = config.get(["global", "api_endpoint"])
        endpoint: str = f"/teams/{team_slug}/features"
        json_response = [
            {"enabled": False, "name": "WORKFLOW_V2"},
            {"enabled": True, "name": "BLIND_STAGE"},
        ]

        responses.add(responses.GET, api + endpoint, json=json_response, status=200)

        assert client.get_team_features(team_slug) == [
            Feature(name="WORKFLOW_V2", enabled=False),
            Feature(name="BLIND_STAGE", enabled=True),
        ]
