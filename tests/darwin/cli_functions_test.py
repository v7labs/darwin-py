from unittest.mock import call, patch

import pytest
import responses
from rich.console import Console
from tests.fixtures import *

from darwin.cli_functions import upload_data
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset


def describe_upload_data():
    @pytest.fixture
    def remote_dataset(dataset_slug: str, local_config_file: Config):
        client = Client(local_config_file)
        return RemoteDataset(client=client, team="v7", name="TEST_DATASET", slug=dataset_slug, dataset_id=1)

    @pytest.fixture
    def request_upload_endpoint(team_slug: str, dataset_slug: str):
        return f"http://localhost/api/teams/{team_slug}/datasets/{dataset_slug}/data"

    @pytest.mark.usefixtures("file_read_write_test")
    @responses.activate
    def default_non_verbose(
        team_slug: str, dataset_slug: str, remote_dataset: RemoteDataset, request_upload_endpoint: str
    ):
        request_upload_response = {
            "blocked_items": [
                {"dataset_item_id": 1, "filename": "test_1.jpg", "path": "/", "reason": "ALREADY_EXISTS"},
                {"dataset_item_id": 2, "filename": "test_2.jpg", "path": "/", "reason": "UNKNOWN_TAGS"},
            ],
            "items": [{"dataset_item_id": 3, "filename": "test_3.jpg", "path": "/"}],
        }

        responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)

        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(Console, "print", return_value=None) as print_mock:
                upload_data(
                    f"{team_slug}/{dataset_slug}",
                    ["test_1.jpg", "test_2.jpg", "test_3.jpg"],
                    [],
                    0,
                    None,
                    None,
                    False,
                    False,
                )
                get_remote_dataset_mock.assert_called_once()

                assert call("Skipped 1 files already in the dataset.\n", style="warning") in print_mock.call_args_list
                assert (
                    call("2 files couldn't be uploaded because an error occurred.\n", style="error")
                    in print_mock.call_args_list
                )
                assert call('Re-run with "--verbose" for further details') in print_mock.call_args_list

    @pytest.mark.usefixtures("file_read_write_test")
    @responses.activate
    def with_verbose_flag(
        team_slug: str, dataset_slug: str, remote_dataset: RemoteDataset, request_upload_endpoint: str
    ):
        request_upload_response = {
            "blocked_items": [
                {"dataset_item_id": 1, "filename": "test_1.jpg", "path": "/", "reason": "ALREADY_EXISTS"},
                {"dataset_item_id": 2, "filename": "test_2.jpg", "path": "/", "reason": "UNKNOWN_TAGS"},
            ],
            "items": [{"dataset_item_id": 3, "filename": "test_3.jpg", "path": "/"}],
        }

        responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)

        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(Console, "print", return_value=None) as print_mock:
                upload_data(
                    f"{team_slug}/{dataset_slug}",
                    ["test_1.jpg", "test_2.jpg", "test_3.jpg"],
                    [],
                    0,
                    None,
                    None,
                    False,
                    True,
                )
                get_remote_dataset_mock.assert_called_once()

                assert call("Skipped 1 files already in the dataset.\n", style="warning") in print_mock.call_args_list
                assert (
                    call("2 files couldn't be uploaded because an error occurred.\n", style="error")
                    in print_mock.call_args_list
                )
                assert call('Re-run with "--verbose" for further details') not in print_mock.call_args_list
