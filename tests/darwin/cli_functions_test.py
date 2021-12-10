import builtins
import logging
import sys
from unittest.mock import call, patch

import pytest
import responses
from rich.console import Console
from tests.fixtures import *

from darwin.cli_functions import delete_files, set_file_status, upload_data
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset


@pytest.fixture
def remote_dataset(dataset_slug: str, local_config_file: Config):
    client = Client(local_config_file)
    return RemoteDataset(client=client, team="v7", name="TEST_DATASET", slug=dataset_slug, dataset_id=1)


def describe_upload_data():
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
                    False,
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


def describe_set_file_status():
    @pytest.fixture
    def dataset_identifier(team_slug: str, dataset_slug: str):
        return f"{team_slug}/{dataset_slug}"

    def raises_if_status_not_supported(dataset_identifier: str):
        with pytest.raises(SystemExit) as exception:
            set_file_status(dataset_identifier, "unknown", [])
            assert exception.value.code == 1

    def calls_dataset_archive(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDataset, "archive") as mock:
                    set_file_status(dataset_identifier, "archived", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def calls_dataset_clear(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDataset, "reset") as mock:
                    set_file_status(dataset_identifier, "clear", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def calls_dataset_new(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDataset, "move_to_new") as mock:
                    set_file_status(dataset_identifier, "new", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def calls_dataset_restore_archived(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDataset, "restore_archived") as mock:
                    set_file_status(dataset_identifier, "restore-archived", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)


def describe_delete_files():
    @pytest.fixture
    def dataset_identifier(team_slug: str, dataset_slug: str):
        return f"{team_slug}/{dataset_slug}"

    def test_bypasses_user_prompt_if_yes_flag_is_true(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDataset, "delete_items") as mock:
                    delete_files(dataset_identifier, ["one.jpg", "two.jpg"], True)
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def test_deletes_items_if_user_accepts_prompt(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(builtins, "input", lambda _: "y"):
                    with patch.object(RemoteDataset, "delete_items") as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"])
                        get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                        fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                        mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def test_does_not_delete_items_if_user_refuses_prompt(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(builtins, "input", lambda _: "n"):
                    with patch.object(RemoteDataset, "delete_items") as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"])
                        get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                        fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                        mock.assert_not_called()

    def test_exits_if_error_occurs(dataset_identifier: str, remote_dataset: RemoteDataset):
        def error_mock():
            raise ValueError("Something went Wrong")

        with patch.object(sys, "exit") as exception:
            with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
                with patch.object(RemoteDataset, "fetch_remote_files") as fetch_remote_files_mock:
                    with patch.object(RemoteDataset, "delete_items", side_effect=error_mock) as mock:

                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"], True)

                        get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                        fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                        mock.assert_called_once_with(fetch_remote_files_mock.return_value)
                        exception.assert_called_once_with(1)

