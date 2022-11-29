from pathlib import Path
from typing import Any, Dict, List

import pytest
import responses
from tests.fixtures import *

from darwin.client import Client
from darwin.config import Config
from darwin.dataset.remote_dataset_v1 import RemoteDatasetV1
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.datatypes import Feature
from darwin.exceptions import NameTaken, NotFound


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
        team_slug: str = "v7"
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

        for version in [RemoteDatasetV1, RemoteDatasetV2]:
            expected_dataset_1 = version(
                team=team_slug,
                name="dataset-name-1",
                slug="dataset-slug-1",
                dataset_id=1,
                item_count=1,
                client=darwin_client,
            )
            expected_dataset_2 = version(
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
            darwin_client.get_remote_dataset("v7/dataset-slug-2")

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

        actual_dataset = darwin_client.get_remote_dataset("v7/dataset-slug-1")
        for version in [RemoteDatasetV1, RemoteDatasetV2]:
            expected_dataset = version(
                team="v7",
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

        actual_dataset = darwin_client.create_dataset("my-dataset", "v7")
        expected_dataset = RemoteDatasetV1(
            team="v7",
            name="my-dataset",
            slug="my-dataset",
            dataset_id=1,
            item_count=1,
            client=darwin_client,
        )

        assert_dataset(actual_dataset, expected_dataset)

    @responses.activate
    def it_raises_if_name_is_taken(darwin_client: Client):
        endpoint: str = "/datasets"
        json_response: Dict[str, Any] = {"errors": {"name": ["has already been taken"]}}

        responses.add(
            responses.POST,
            darwin_client.url + endpoint,
            json=json_response,
            status=422,
            adding_headers={"content-type": "utf-8"},
        )

        with pytest.raises(NameTaken):
            darwin_client.create_dataset("my-dataset", "v7")


@pytest.mark.usefixtures("file_read_write_test")
def describe_fetch_remote_files():
    @responses.activate
    def it_returns_remote_files(darwin_client: Client):
        dataset_id = 1
        endpoint: str = f"/datasets/{dataset_id}/items?page%5Bsize%5D=500&page%5Bfrom%5D=0"
        responses.add(responses.POST, darwin_client.url + endpoint, json={}, status=200)

        darwin_client.fetch_remote_files(dataset_id, {"page[size]": 500, "page[from]": 0}, {}, "v7")


@pytest.mark.usefixtures("file_read_write_test")
def describe_fetch_remote_classes():
    @responses.activate
    def it_returns_remote_classes(team_slug: str, darwin_client: Client):
        endpoint: str = f"/teams/{team_slug}/annotation_classes?include_tags=true"
        response: Dict[str, Any] = {
            "annotation_classes": [
                {
                    "annotation_class_image_url": None,
                    "annotation_types": ["tag"],
                    "dataset_id": 215,
                    "datasets": [{"id": 215}, {"id": 265}],
                    "description": " Tag 2",
                    "id": 345,
                    "images": [],
                    "inserted_at": "2021-01-25T02:27:10",
                    "metadata": {"_color": "rgba(0,255,0,1.0)", "tag": {}},
                    "name": " Tag 2",
                    "team_id": 2,
                    "updated_at": "2021-01-25T02:27:10",
                }
            ]
        }

        responses.add(responses.GET, darwin_client.url + endpoint, json=response, status=200)

        result: List[Dict[str, Any]] = darwin_client.fetch_remote_classes(team_slug)
        annotation_class: Dict[str, Any] = result[0]

        assert annotation_class["annotation_class_image_url"] is None
        assert annotation_class["annotation_types"] == ["tag"]
        assert annotation_class["dataset_id"] == 215
        assert annotation_class["datasets"] == [{"id": 215}, {"id": 265}]
        assert annotation_class["id"] == 345


@pytest.mark.usefixtures("file_read_write_test")
def describe_get_team_features():
    @responses.activate
    def it_returns_list_of_features(team_slug: str, darwin_client: Client):
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


@pytest.mark.usefixtures("file_read_write_test")
def describe_instantiate_item():
    @responses.activate
    def it_raises_if_workflow_id_is_not_found(darwin_client: Client):
        item_id: int = 1234
        endpoint: str = f"/dataset_items/{item_id}/workflow"
        json_response: Dict[str, Any] = {}

        responses.add(responses.POST, darwin_client.url + endpoint, json=json_response, status=200)

        with pytest.raises(ValueError) as exception:
            darwin_client.instantiate_item(item_id)

        assert str(exception.value) == f"No Workflow Id found for item_id: {item_id}"

    @responses.activate
    def it_returns_workflow_id(darwin_client: Client):
        item_id: int = 1234
        workflow_id: int = 1
        endpoint: str = f"/dataset_items/{item_id}/workflow"
        json_response: Dict[str, Any] = {"current_workflow_id": workflow_id}

        responses.add(responses.POST, darwin_client.url + endpoint, json=json_response, status=200)
        assert darwin_client.instantiate_item(item_id) == workflow_id


@pytest.mark.usefixtures("file_read_write_test")
def describe_post_workflow_comment():
    @responses.activate
    def it_raises_if_comment_id_is_not_found(darwin_client: Client):
        workflow_id = 1234
        endpoint: str = f"/workflows/{workflow_id}/workflow_comment_threads"
        json_response: Dict[str, Any] = {}

        responses.add(responses.POST, darwin_client.url + endpoint, json=json_response, status=200)

        with pytest.raises(ValueError) as exception:
            darwin_client.post_workflow_comment(workflow_id, "My comment.")

        assert str(exception.value) == f"Unable to retrieve comment id for workflow: {workflow_id}."

    @responses.activate
    def it_returns_comment_id(darwin_client: Client):
        comment_id: int = 1234
        workflow_id: int = 1
        endpoint: str = f"/workflows/{workflow_id}/workflow_comment_threads"
        json_response: Dict[str, Any] = {"id": comment_id}

        responses.add(responses.POST, darwin_client.url + endpoint, json=json_response, status=200)
        assert darwin_client.post_workflow_comment(workflow_id, "My comment.") == comment_id


def assert_dataset(dataset_1, dataset_2):
    assert dataset_1.name == dataset_2.name
    assert dataset_1.team == dataset_2.team
    assert dataset_1.dataset_id == dataset_2.dataset_id
    assert dataset_1.slug == dataset_2.slug
    assert dataset_1.item_count == dataset_2.item_count
