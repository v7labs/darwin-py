from pathlib import Path
from typing import Any, Dict, List

import pytest
import responses
from tests.fixtures import *

from darwin.client import Client
from darwin.config import Config
from darwin.dataset.remote_dataset import RemoteDataset
from darwin.datatypes import Feature
from darwin.exceptions import NotFound


@pytest.fixture
def darwin_client(darwin_config_path: Path, darwin_datasets_path: Path, team_slug: str) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug, "api_key"], "mock_api_key")
    config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
    return Client(config)


@pytest.mark.usefixtures("file_read_write_test")
def describe_list_remote_datasets():
    @responses.activate
    def it_returns_list_of_datasets(darwin_client: Client):
        team_slug: str = "team-slug"
        endpoint: str = "/datasets"
        json_response: List[Dict[str, Any]] = [
            {
                "name": "dataset-name-1",
                "slug": "dataset-slug-1",
                "id": 1,
                "num_images": 1,
                "num_videos": 0,
                "progress": 0,
            },
            {
                "name": "dataset-name-2",
                "slug": "dataset-slug-2",
                "id": 2,
                "num_images": 2,
                "num_videos": 0,
                "progress": 0,
            },
        ]

        responses.add(responses.GET, darwin_client.url + endpoint, json=json_response, status=200)

        remote_datasets = list(darwin_client.list_remote_datasets(team_slug))
        expected_dataset_1 = RemoteDataset(
            team=team_slug,
            name="dataset-name-1",
            slug="dataset-slug-1",
            dataset_id=1,
            item_count=1,
            client=darwin_client,
        )
        expected_dataset_2 = RemoteDataset(
            team=team_slug,
            name="dataset-name-2",
            slug="dataset-slug-2",
            dataset_id=2,
            item_count=2,
            client=darwin_client,
        )

        assert_dataset(remote_datasets[0], expected_dataset_1)
        assert_dataset(remote_datasets[1], expected_dataset_2)


@pytest.mark.usefixtures("file_read_write_test")
def describe_get_remote_dataset():
    @responses.activate
    def it_raises_if_dataset_is_not_found(darwin_client: Client):
        endpoint: str = "/datasets"
        json_response = [
            {
                "name": "dataset-name-1",
                "slug": "dataset-slug-1",
                "id": 1,
                "num_images": 1,
                "num_videos": 0,
                "progress": 0,
            }
        ]

        responses.add(responses.GET, darwin_client.url + endpoint, json=json_response, status=200)

        with pytest.raises(NotFound):
            darwin_client.get_remote_dataset("team-slug/dataset-slug-2")

    @responses.activate
    def it_returns_the_dataset(darwin_client: Client):
        endpoint: str = "/datasets"
        json_response = [
            {
                "name": "dataset-name-1",
                "slug": "dataset-slug-1",
                "id": 1,
                "num_images": 1,
                "num_videos": 0,
                "progress": 0,
            }
        ]

        responses.add(responses.GET, darwin_client.url + endpoint, json=json_response, status=200)

        actual_dataset = darwin_client.get_remote_dataset("team-slug/dataset-slug-1")
        expected_dataset = RemoteDataset(
            team="team-slug",
            name="dataset-name-1",
            slug="dataset-slug-1",
            dataset_id=1,
            item_count=1,
            client=darwin_client,
        )

        assert_dataset(actual_dataset, expected_dataset)


@pytest.mark.usefixtures("file_read_write_test")
def describe_create_dataset():
    @responses.activate
    def it_returns_the_created_dataset(darwin_client: Client):
        endpoint: str = "/datasets"
        json_response: Dict[str, Any] = {
            "name": "my-dataset",
            "slug": "my-dataset",
            "id": 1,
            "num_images": 1,
            "num_videos": 0,
            "progress": 0,
        }

        responses.add(responses.POST, darwin_client.url + endpoint, json=json_response, status=200)

        actual_dataset = darwin_client.create_dataset("my-dataset", "team-slug")
        expected_dataset = RemoteDataset(
            team="team-slug", name="my-dataset", slug="my-dataset", dataset_id=1, item_count=1, client=darwin_client,
        )

        assert_dataset(actual_dataset, expected_dataset)


@pytest.mark.usefixtures("file_read_write_test")
def describe_get_team_features():
    @responses.activate
    def it_returns_list_of_features(darwin_client: Client):
        team_slug: str = "team-slug"
        endpoint: str = f"/teams/{team_slug}/features"
        json_response = [
            {"enabled": False, "name": "WORKFLOW_V2"},
            {"enabled": True, "name": "BLIND_STAGE"},
        ]

        responses.add(responses.GET, darwin_client.url + endpoint, json=json_response, status=200)

        assert darwin_client.get_team_features(team_slug) == [
            Feature(name="WORKFLOW_V2", enabled=False),
            Feature(name="BLIND_STAGE", enabled=True),
        ]


def assert_dataset(dataset_1, dataset_2):
    assert dataset_1.name == dataset_2.name
    assert dataset_1.team == dataset_2.team
    assert dataset_1.dataset_id == dataset_2.dataset_id
    assert dataset_1.slug == dataset_2.slug
    assert dataset_1.item_count == dataset_2.item_count
