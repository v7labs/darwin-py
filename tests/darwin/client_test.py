from pathlib import Path
from typing import Any, Dict

import pytest
import responses

from darwin.client import Client
from darwin.config import Config
from darwin.datatypes import Feature
from darwin.exceptions import InsufficientStorage, Unauthorized


def describe_put():
    @responses.activate
    def it_raises_if_request_is_unauthorized():
        team_slug: str = "team-slug"
        dataset_slug: str = "dataset-slug"
        upload_payload: Dict[Any, Any] = {"key": "value"}

        darwin_datasets_path: Path = Path.home() / ".darwin" / "datasets"

        config = Config()
        config.put(["global", "api_endpoint"], "http://localhost/api")
        config.put(["global", "base_url"], "http://localhost")
        config.put(["teams", team_slug, "api_key"], "mock_api_key")
        config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
        client = Client(config)

        api: str = config.get(["global", "api_endpoint"])
        endpoint: str = f"/teams/{team_slug}/datasets/{dataset_slug}/data"

        responses.add(responses.PUT, api + endpoint, status=401)

        with pytest.raises(Unauthorized):
            client.put(endpoint=endpoint, payload=upload_payload, team=team_slug)

    @responses.activate
    def it_raises_if_there_is_not_enough_storage():
        team_slug: str = "team-slug"
        dataset_slug: str = "dataset-slug"
        upload_payload: Dict[Any, Any] = {"key": "value"}

        darwin_datasets_path: Path = Path.home() / ".darwin" / "datasets"

        config = Config()
        config.put(["global", "api_endpoint"], "http://localhost/api")
        config.put(["global", "base_url"], "http://localhost")
        config.put(["teams", team_slug, "api_key"], "mock_api_key")
        config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
        client = Client(config)

        api: str = config.get(["global", "api_endpoint"])
        endpoint: str = f"/teams/{team_slug}/datasets/{dataset_slug}/data"

        responses.add(
            responses.PUT, api + endpoint, json={"errors": {"code": "INSUFFICIENT_REMAINING_STORAGE"}}, status=429
        )

        with pytest.raises(InsufficientStorage):
            client.put(endpoint=endpoint, payload=upload_payload, team=team_slug)

    @responses.activate
    def it_returns_content_if_status_is_429_but_error_code_is_unknown():
        team_slug: str = "team-slug"
        dataset_slug: str = "dataset-slug"
        upload_payload: Dict[Any, Any] = {"key": "value"}

        darwin_datasets_path: Path = Path.home() / ".darwin" / "datasets"

        config = Config()
        config.put(["global", "api_endpoint"], "http://localhost/api")
        config.put(["global", "base_url"], "http://localhost")
        config.put(["teams", team_slug, "api_key"], "mock_api_key")
        config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
        client = Client(config)

        api: str = config.get(["global", "api_endpoint"])
        endpoint: str = f"/teams/{team_slug}/datasets/{dataset_slug}/data"
        json_response = {"errors": {"code": "SOME_ERROR"}}

        responses.add(responses.PUT, api + endpoint, json=json_response, status=429)

        response = client.put(endpoint=endpoint, payload=upload_payload, team=team_slug)

        assert response == json_response


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
        client = Client(config)

        api: str = config.get(["global", "api_endpoint"])
        endpoint: str = f"/teams/{team_slug}/features"
        json_response = [
            {"enabled": False, "name": "WORKFLOW_V2"},
            {"enabled": True, "name": "BLIND_STAGE"},
        ]

        responses.add(responses.GET, api + endpoint, json=json_response, status=429)

        assert client.get_team_features(team_slug) == [
            Feature(name="WORKFLOW_V2", enabled=False),
            Feature(name="BLIND_STAGE", enabled=True),
        ]
