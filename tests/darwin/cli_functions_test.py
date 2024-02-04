import builtins
import sys
from unittest.mock import call, patch

import pytest
import responses
from rich.console import Console

from darwin.cli_functions import delete_files, set_file_status, upload_data
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from tests.fixtures import *


@pytest.fixture
def remote_dataset(
    team_slug_darwin_json_v2: str, dataset_slug: str, local_config_file: Config
):
    client = Client(local_config_file)
    return RemoteDatasetV2(
        client=client,
        team=team_slug_darwin_json_v2,
        name="TEST_DATASET",
        slug=dataset_slug,
        dataset_id=1,
    )


@pytest.fixture
def request_upload_endpoint(team_slug_darwin_json_v2: str, dataset_slug: str):
    return f"http://localhost/api/teams/{team_slug_darwin_json_v2}/datasets/{dataset_slug}/data"


class TestUploadData:
    @pytest.fixture
    def request_upload_endpoint(self, team_slug_darwin_json_v2: str, dataset_slug: str):
        return f"http://localhost/api/v2/teams/{team_slug_darwin_json_v2}/items/register_upload"

    @pytest.mark.usefixtures("file_read_write_test")
    @responses.activate
    def test_default_non_verbose(
        self,
        team_slug_darwin_json_v2: str,
        dataset_slug: str,
        remote_dataset: RemoteDataset,
        request_upload_endpoint: str,
    ):
        request_upload_response = response = {
            "blocked_items": [
                {
                    "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                    "name": "test_1.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_1.jpg",
                            "reason": "ALREADY_EXISTS",
                            "slot_name": "0",
                            "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                            "as_frames": False,
                            "extract_views": False,
                        }
                    ],
                },
                {
                    "id": "4b351102-f3cc-4356-9daf-5237d567b965",
                    "name": "test_2.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_2.jpg",
                            "reason": "UNKNOWN_TAGS",
                            "slot_name": "0",
                            "upload_id": "223f5678-f90c-23e4-b567-527725185001",
                            "as_frames": False,
                            "extract_views": False,
                        }
                    ],
                },
            ],
            "items": [
                {
                    "id": "5b461103-g4dd-4457-0eaf-6338e568c966",
                    "name": "test_3.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_3.jpg",
                            "slot_name": "0",
                            "upload_id": "323g6789-g01d-34f5-c678-628836196002",
                            "as_frames": False,
                            "extract_views": False,
                        }
                    ],
                }
            ],
        }

        responses.add(
            responses.POST,
            request_upload_endpoint,
            json=request_upload_response,
            status=200,
        )

        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(Console, "print", return_value=None) as print_mock:
                upload_data(
                    f"{team_slug_darwin_json_v2}/{dataset_slug}",
                    ["test_1.jpg", "test_2.jpg", "test_3.jpg"],
                    [],
                    0,
                    None,
                    False,
                    False,
                    False,
                    False,
                )
                get_remote_dataset_mock.assert_called_once()

                assert (
                    call("Skipped 1 files already in the dataset.\n", style="warning")
                    in print_mock.call_args_list
                )
                assert (
                    call(
                        "2 files couldn't be uploaded because an error occurred.\n",
                        style="error",
                    )
                    in print_mock.call_args_list
                )
                assert (
                    call('Re-run with "--verbose" for further details')
                    in print_mock.call_args_list
                )

    @pytest.mark.usefixtures("file_read_write_test")
    @responses.activate
    def test_with_verbose_flag(
        self,
        team_slug_darwin_json_v2: str,
        dataset_slug: str,
        remote_dataset: RemoteDataset,
        request_upload_endpoint: str,
    ):
        request_upload_response = response = {
            "blocked_items": [
                {
                    "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                    "name": "test_1.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_1.jpg",
                            "reason": "ALREADY_EXISTS",
                            "slot_name": "0",
                            "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                            "as_frames": False,
                            "extract_views": False,
                        }
                    ],
                },
                {
                    "id": "4b351102-f3cc-4356-9daf-5237d567b965",
                    "name": "test_2.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_2.jpg",
                            "reason": "UNKNOWN_TAGS",
                            "slot_name": "0",
                            "upload_id": "223f5678-f90c-23e4-b567-527725185001",
                            "as_frames": False,
                            "extract_views": False,
                        }
                    ],
                },
            ],
            "items": [
                {
                    "id": "5b461103-g4dd-4457-0eaf-6338e568c966",
                    "name": "test_3.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_3.jpg",
                            "slot_name": "0",
                            "upload_id": "323g6789-g01d-34f5-c678-628836196002",
                            "as_frames": False,
                            "extract_views": False,
                        }
                    ],
                }
            ],
        }

        responses.add(
            responses.POST,
            request_upload_endpoint,
            json=request_upload_response,
            status=200,
        )

        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(Console, "print", return_value=None) as print_mock:
                upload_data(
                    f"{team_slug_darwin_json_v2}/{dataset_slug}",
                    ["test_1.jpg", "test_2.jpg", "test_3.jpg"],
                    [],
                    0,
                    None,
                    None,
                    False,
                    False,
                    True,
                )
                get_remote_dataset_mock.assert_called_once()

                assert (
                    call("Skipped 1 files already in the dataset.\n", style="warning")
                    in print_mock.call_args_list
                )
                assert (
                    call(
                        "2 files couldn't be uploaded because an error occurred.\n",
                        style="error",
                    )
                    in print_mock.call_args_list
                )
                assert (
                    call('Re-run with "--verbose" for further details')
                    not in print_mock.call_args_list
                )


class TestSetFileStatus:
    @pytest.fixture
    def dataset_identifier(self, team_slug_darwin_json_v2: str, dataset_slug: str):
        return f"{team_slug_darwin_json_v2}/{dataset_slug}"

    def test_raises_if_status_not_supported(self, dataset_identifier: str):
        with pytest.raises(SystemExit) as exception:
            set_file_status(dataset_identifier, "unknown", [])
            assert exception.value.code == 1

    def test_calls_dataset_archive(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV2, "archive") as mock:
                    set_file_status(
                        dataset_identifier, "archived", ["one.jpg", "two.jpg"]
                    )
                    get_remote_dataset_mock.assert_called_once_with(
                        dataset_identifier=dataset_identifier
                    )
                    fetch_remote_files_mock.assert_called_once_with(
                        {"filenames": "one.jpg,two.jpg"}
                    )
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def test_calls_dataset_clear(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV2, "reset") as mock:
                    set_file_status(dataset_identifier, "clear", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(
                        dataset_identifier=dataset_identifier
                    )
                    fetch_remote_files_mock.assert_called_once_with(
                        {"filenames": "one.jpg,two.jpg"}
                    )
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def test_calls_dataset_new(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV2, "move_to_new") as mock:
                    set_file_status(dataset_identifier, "new", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(
                        dataset_identifier=dataset_identifier
                    )
                    fetch_remote_files_mock.assert_called_once_with(
                        {"filenames": "one.jpg,two.jpg"}
                    )
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def test_calls_dataset_restore_archived(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV2, "restore_archived") as mock:
                    set_file_status(
                        dataset_identifier, "restore-archived", ["one.jpg", "two.jpg"]
                    )
                    get_remote_dataset_mock.assert_called_once_with(
                        dataset_identifier=dataset_identifier
                    )
                    fetch_remote_files_mock.assert_called_once_with(
                        {"filenames": "one.jpg,two.jpg"}
                    )
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)


class TestDeleteFiles:
    @pytest.fixture
    def dataset_identifier(self, team_slug_darwin_json_v2: str, dataset_slug: str):
        return f"{team_slug_darwin_json_v2}/{dataset_slug}"

    def test_bypasses_user_prompt_if_yes_flag_is_true(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV2, "delete_items") as mock:
                    delete_files(dataset_identifier, ["one.jpg", "two.jpg"], True)
                    get_remote_dataset_mock.assert_called_once_with(
                        dataset_identifier=dataset_identifier
                    )
                    fetch_remote_files_mock.assert_called_once_with(
                        {"filenames": ["one.jpg", "two.jpg"]}
                    )
                    mock.assert_called_once()

    def test_deletes_items_if_user_accepts_prompt(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(builtins, "input", lambda _: "y"):
                    with patch.object(RemoteDatasetV2, "delete_items") as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"])
                        get_remote_dataset_mock.assert_called_once_with(
                            dataset_identifier=dataset_identifier
                        )
                        fetch_remote_files_mock.assert_called_once_with(
                            {"filenames": ["one.jpg", "two.jpg"]}
                        )
                        mock.assert_called_once()

    def test_does_not_delete_items_if_user_refuses_prompt(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        with patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset
        ) as get_remote_dataset_mock:
            with patch.object(
                RemoteDatasetV2, "fetch_remote_files"
            ) as fetch_remote_files_mock:
                with patch.object(builtins, "input", lambda _: "n"):
                    with patch.object(RemoteDatasetV2, "delete_items") as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"])
                        get_remote_dataset_mock.assert_called_once_with(
                            dataset_identifier=dataset_identifier
                        )
                        fetch_remote_files_mock.assert_called_once_with(
                            {"filenames": ["one.jpg", "two.jpg"]}
                        )
                        mock.assert_not_called()

    def test_exits_if_error_occurs(
        self, dataset_identifier: str, remote_dataset: RemoteDataset
    ):
        def error_mock():
            raise ValueError("Something went Wrong")

        with patch.object(sys, "exit") as exception:
            with patch.object(
                Client, "get_remote_dataset", return_value=remote_dataset
            ) as get_remote_dataset_mock:
                with patch.object(
                    RemoteDatasetV2, "fetch_remote_files"
                ) as fetch_remote_files_mock:
                    with patch.object(
                        RemoteDatasetV2, "delete_items", side_effect=error_mock
                    ) as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"], True)

                        get_remote_dataset_mock.assert_called_once_with(
                            dataset_identifier=dataset_identifier
                        )
                        fetch_remote_files_mock.assert_called_once_with(
                            {"filenames": ["one.jpg", "two.jpg"]}
                        )
                        mock.assert_called_once()
                        exception.assert_called_once_with(1)
