from pathlib import Path
from typing import List

import pytest
import responses

from darwin.client import Client
from darwin.config import Config
from darwin.dataset.remote_dataset import RemoteDataset
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.datatypes import Feature, JSONFreeForm
from darwin.exceptions import NameTaken, NotFound
from darwin.future.data_objects.properties import FullProperty
from darwin.future.tests.core.fixtures import *  # noqa: F401, F403
from tests.fixtures import *  # noqa: F401, F403


@pytest.fixture
def darwin_client(
    darwin_config_path: Path, darwin_datasets_path: Path, team_slug_darwin_json_v2: str
) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug_darwin_json_v2, "api_key"], "mock_api_key")
    config.put(
        ["teams", team_slug_darwin_json_v2, "datasets_dir"], str(darwin_datasets_path)
    )
    return Client(config)


@pytest.mark.usefixtures("file_read_write_test")
class TestListRemoteDatasets:
    @responses.activate
    def test_returns_list_of_datasets(self, darwin_client: Client) -> None:
        team_slug: str = "v7"
        endpoint: str = "/datasets"
        json_response: List[JSONFreeForm] = [
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

        responses.add(
            responses.GET, darwin_client.url + endpoint, json=json_response, status=200
        )

        remote_datasets = list(darwin_client.list_remote_datasets(team_slug))

        expected_dataset_1 = RemoteDatasetV2(
            team=team_slug,
            name="dataset-name-1",
            slug="dataset-slug-1",
            dataset_id=1,
            item_count=1,
            client=darwin_client,
        )
        expected_dataset_2 = RemoteDatasetV2(
            team=team_slug,
            name="dataset-name-2",
            slug="dataset-slug-2",
            dataset_id=2,
            item_count=2,
            client=darwin_client,
        )

        assert_dataset(remote_datasets[0], expected_dataset_1)
        assert_dataset(remote_datasets[1], expected_dataset_2)

    @responses.activate
    def test_coalesces_null_item_counts_to_zeroes(self, darwin_client: Client) -> None:
        team_slug: str = "v7"
        endpoint: str = "/datasets"
        json_response: List[JSONFreeForm] = [
            {
                "name": "dataset-name-1",
                "slug": "dataset-slug-1",
                "id": 1,
                "num_items": None,  # As this is None, num_images and num_videos should be used
                "num_images": None,  # Should be coalesced to 0
                "num_videos": None,  # Should be coalesced to 0
                "progress": 4,
            },
            {
                "name": "dataset-name-2",
                "slug": "dataset-slug-2",
                "id": 2,
                "num_items": None,  # As this is None, num_images and num_videos should be used
                "num_images": 2,  # Should be used
                "num_videos": 3,  # Should be used
                "progress": 32,
            },
            {
                "name": "dataset-name-3",
                "slug": "dataset-slug-3",
                "id": 3,
                "num_items": 11,  # Should be used
                "num_images": 2,  # Should be ignored, as num_items is present
                "num_videos": 3,  # Should be ignored, as num_items is present
                "progress": 32,
            },
        ]

        responses.add(
            responses.GET, darwin_client.url + endpoint, json=json_response, status=200
        )

        remote_datasets = list(darwin_client.list_remote_datasets(team_slug))

        expected_item_count = [0, 5, 11]
        for i, ds in enumerate(remote_datasets):
            assert ds.item_count == expected_item_count[i]


@pytest.mark.usefixtures("file_read_write_test")
class TestGetRemoteDataset:
    @responses.activate
    def test_raises_if_dataset_is_not_found(self, darwin_client: Client) -> None:
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

        responses.add(
            responses.GET, darwin_client.url + endpoint, json=json_response, status=200
        )

        with pytest.raises(NotFound):
            darwin_client.get_remote_dataset("v7/dataset-slug-2")

    @responses.activate
    def test_returns_the_dataset(self, darwin_client: Client) -> None:
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

        responses.add(
            responses.GET, darwin_client.url + endpoint, json=json_response, status=200
        )

        actual_dataset = darwin_client.get_remote_dataset("v7/dataset-slug-1")
        expected_dataset = RemoteDatasetV2(
            team="v7",
            name="dataset-name-1",
            slug="dataset-slug-1",
            dataset_id=1,
            item_count=1,
            client=darwin_client,
        )

        assert_dataset(actual_dataset, expected_dataset)


@pytest.mark.usefixtures("file_read_write_test")
class TestCreateDataset:
    @responses.activate
    def test_returns_the_created_dataset(self, darwin_client: Client) -> None:
        endpoint: str = "/datasets"
        json_response: JSONFreeForm = {
            "name": "my-dataset",
            "slug": "my-dataset",
            "id": 1,
            "num_images": 1,
            "num_videos": 0,
            "progress": 0,
        }

        responses.add(
            responses.POST, darwin_client.url + endpoint, json=json_response, status=200
        )

        actual_dataset = darwin_client.create_dataset("my-dataset", "v7")
        expected_dataset = RemoteDatasetV2(
            team="v7",
            name="my-dataset",
            slug="my-dataset",
            dataset_id=1,
            item_count=1,
            client=darwin_client,
        )

        assert_dataset(actual_dataset, expected_dataset)

    @responses.activate
    def test_raises_if_name_is_taken(self, darwin_client: Client) -> None:
        endpoint: str = "/datasets"
        json_response: JSONFreeForm = {"errors": {"name": ["has already been taken"]}}

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
class TestFetchRemoteFiles:
    @responses.activate
    def test_returns_remote_files(self, darwin_client: Client) -> None:
        dataset_id = 1
        endpoint: str = (
            f"/datasets/{dataset_id}/items?page%5Bsize%5D=500&page%5Bfrom%5D=0"
        )
        responses.add(responses.POST, darwin_client.url + endpoint, json={}, status=200)

        darwin_client.fetch_remote_files(
            dataset_id, {"page[size]": 500, "page[from]": 0}, {}, "v7"
        )


@pytest.mark.usefixtures("file_read_write_test")
class TestFetchRemoteClasses:
    @responses.activate
    def test_returns_remote_classes(
        self, team_slug_darwin_json_v2: str, darwin_client: Client
    ) -> None:
        endpoint: str = (
            f"/teams/{team_slug_darwin_json_v2}/annotation_classes?include_tags=true"
        )
        response: JSONFreeForm = {
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

        responses.add(
            responses.GET, darwin_client.url + endpoint, json=response, status=200
        )

        result: List[JSONFreeForm] = darwin_client.fetch_remote_classes(
            team_slug_darwin_json_v2
        )
        annotation_class: JSONFreeForm = result[0]

        assert annotation_class["annotation_class_image_url"] is None
        assert annotation_class["annotation_types"] == ["tag"]
        assert annotation_class["dataset_id"] == 215
        assert annotation_class["datasets"] == [{"id": 215}, {"id": 265}]
        assert annotation_class["id"] == 345


@pytest.mark.usefixtures("file_read_write_test")
class TestGetTeamFeatures:
    @responses.activate
    def test_returns_list_of_features(
        self, team_slug_darwin_json_v2: str, darwin_client: Client
    ) -> None:
        endpoint: str = f"/teams/{team_slug_darwin_json_v2}/features"
        json_response = [
            {"enabled": False, "name": "WORKFLOW_V2"},
            {"enabled": True, "name": "BLIND_STAGE"},
        ]

        responses.add(
            responses.GET, darwin_client.url + endpoint, json=json_response, status=200
        )

        assert darwin_client.get_team_features(team_slug_darwin_json_v2) == [
            Feature(name="WORKFLOW_V2", enabled=False),
            Feature(name="BLIND_STAGE", enabled=True),
        ]


@pytest.mark.usefixtures("file_read_write_test")
class TestInstantiateItem:
    @responses.activate
    def test_raises_if_workflow_id_is_not_found(self, darwin_client: Client) -> None:
        item_id: int = 1234
        endpoint: str = f"/dataset_items/{item_id}/workflow"
        json_response: JSONFreeForm = {}

        responses.add(
            responses.POST, darwin_client.url + endpoint, json=json_response, status=200
        )

        with pytest.raises(ValueError) as exception:
            darwin_client.instantiate_item(item_id)

        assert str(exception.value) == f"No Workflow Id found for item_id: {item_id}"

    @responses.activate
    def test_returns_workflow_id(self, darwin_client: Client) -> None:
        item_id: int = 1234
        workflow_id: int = 1
        endpoint: str = f"/dataset_items/{item_id}/workflow"
        json_response: JSONFreeForm = {"current_workflow_id": workflow_id}

        responses.add(
            responses.POST, darwin_client.url + endpoint, json=json_response, status=200
        )
        assert darwin_client.instantiate_item(item_id) == workflow_id


@pytest.mark.usefixtures("file_read_write_test")
class TestWorkflowComment:
    @responses.activate
    def test_raises_if_comment_id_is_not_found(self, darwin_client: Client) -> None:
        workflow_id = 1234
        endpoint: str = f"/workflows/{workflow_id}/workflow_comment_threads"
        json_response: JSONFreeForm = {}

        responses.add(
            responses.POST, darwin_client.url + endpoint, json=json_response, status=200
        )

        with pytest.raises(ValueError) as exception:
            darwin_client.post_workflow_comment(workflow_id, "My comment.")

        assert (
            str(exception.value)
            == f"Unable to retrieve comment id for workflow: {workflow_id}."
        )

    @responses.activate
    def test_returns_comment_id(self, darwin_client: Client) -> None:
        comment_id: int = 1234
        workflow_id: int = 1
        endpoint: str = f"/workflows/{workflow_id}/workflow_comment_threads"
        json_response: JSONFreeForm = {"id": comment_id}

        responses.add(
            responses.POST, darwin_client.url + endpoint, json=json_response, status=200
        )
        assert (
            darwin_client.post_workflow_comment(workflow_id, "My comment.")
            == comment_id
        )


def assert_dataset(dataset_1: RemoteDataset, dataset_2: RemoteDataset) -> None:
    assert dataset_1.name == dataset_2.name
    assert dataset_1.team == dataset_2.team
    assert dataset_1.dataset_id == dataset_2.dataset_id
    assert dataset_1.slug == dataset_2.slug
    assert dataset_1.item_count == dataset_2.item_count


# Tests for _get_item_count
def test__get_item_count_defaults_to_num_items_if_present() -> None:
    dataset_return = {
        "num_images": 2,  # Should be ignored
        "num_videos": 3,  # Should be ignored
        "num_items": 5,  # Should get this one
    }

    assert Client._get_item_count(dataset_return) == 5


def test__get_item_count_returns_sum_of_others_if_num_items_not_present() -> None:
    dataset_return = {
        "num_images": 7,  # Should be summed
        "num_videos": 3,  # Should be summed
    }

    assert Client._get_item_count(dataset_return) == 10


def test__get_item_count_should_tolerate_missing_members() -> None:
    assert (
        Client._get_item_count(
            {
                "num_videos": 3,  # Should be ignored
            }
        )
        == 3
    )

    assert (
        Client._get_item_count(
            {
                "num_images": 2,
            }
        )
        == 2
    )


@pytest.mark.usefixtures("file_read_write_test")
class TestGetTeamProperties:
    @responses.activate
    def test_get_team_properties(self, darwin_client: Client) -> None:
        responses.add(
            responses.GET,
            "http://localhost/apiv2/teams/v7-darwin-json-v2/properties?include_values=true",
            json={
                "properties": [
                    {
                        "annotation_class_id": 2558,
                        "description": "test question",
                        "id": "d7368686-d087-4d92-bfd9-8ae776c3ed3a",
                        "name": "property question",
                        "property_values": [
                            {
                                "color": "rgba(143,255,0,1.0)",
                                "id": "3e40c575-41dc-43c9-87f9-7dc2b625650d",
                                "type": "string",
                                "value": "answer 1",
                            },
                            {
                                "color": "rgba(173,255,0,1.0)",
                                "id": "18ebaad0-c22a-49db-b6c5-1de0da986f4e",
                                "type": "string",
                                "value": "answer 2",
                            },
                            {
                                "color": "rgba(82,255,0,1.0)",
                                "id": "b67ae529-f612-4c9a-a175-5b98f1d81a6e",
                                "type": "string",
                                "value": "answer 3",
                            },
                        ],
                        "required": False,
                        "slug": "property-question",
                        "team_id": 128,
                        "type": "multi_select",
                    },
                ]
            },
            status=200,
        )
        assert len(darwin_client.get_team_properties()) == 1


@pytest.mark.usefixtures("file_read_write_test")
class TestCreateProperty:
    @responses.activate
    def test_create_property(
        self, darwin_client: Client, base_property_object: FullProperty
    ) -> None:
        responses.add(
            responses.POST,
            "http://localhost/apiv2/teams/v7-darwin-json-v2/properties",
            json=base_property_object.dict(),
            status=200,
        )
        _property = darwin_client.create_property(
            team_slug="v7-darwin-json-v2", params=base_property_object
        )
        assert isinstance(_property, FullProperty)
        assert _property == base_property_object

    @responses.activate
    def test_create_property_from_json(
        self, darwin_client: Client, base_property_object: FullProperty
    ) -> None:
        responses.add(
            responses.POST,
            "http://localhost/apiv2/teams/v7-darwin-json-v2/properties",
            json=base_property_object.dict(),
            status=200,
        )
        _property = darwin_client.create_property(
            team_slug="v7-darwin-json-v2", params=base_property_object.dict()
        )
        assert isinstance(_property, FullProperty)
        assert _property == base_property_object


@pytest.mark.usefixtures("file_read_write_test")
class TestUpdateProperty:
    @responses.activate
    def test_update_property(
        self, darwin_client: Client, base_property_object: FullProperty
    ) -> None:
        property_id = base_property_object.id
        responses.add(
            responses.PUT,
            f"http://localhost/apiv2/teams/v7-darwin-json-v2/properties/{property_id}",
            json=base_property_object.dict(),
            status=200,
        )
        _property = darwin_client.update_property(
            team_slug="v7-darwin-json-v2", params=base_property_object
        )
        assert isinstance(_property, FullProperty)
        assert _property == base_property_object

    @responses.activate
    def test_update_property_from_json(
        self, darwin_client: Client, base_property_object: FullProperty
    ) -> None:
        property_id = base_property_object.id
        responses.add(
            responses.PUT,
            f"http://localhost/apiv2/teams/v7-darwin-json-v2/properties/{property_id}",
            json=base_property_object.dict(),
            status=200,
        )
        _property = darwin_client.update_property(
            team_slug="v7-darwin-json-v2", params=base_property_object.dict()
        )
        assert isinstance(_property, FullProperty)
        assert _property == base_property_object
