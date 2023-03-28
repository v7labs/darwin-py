import builtins
import sys
import uuid
from typing import List, Union
from unittest.mock import call, patch

import pytest
import responses
from rich.console import Console

import darwin
import darwin.datatypes as dt
from darwin.cli_functions import (
    begin_evaluation_run,
    delete_files,
    set_file_status,
    upload_data,
)
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.remote_dataset_v1 import RemoteDatasetV1
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.exceptions import NotFound, UnknownAnnotationFileSchema
from darwin.importer.importer import ImportResult
from tests.fixtures import *


@pytest.fixture
def remote_dataset(team_slug: str, dataset_slug: str, local_config_file: Config):
    client = Client(local_config_file)
    return RemoteDatasetV1(client=client, team=team_slug, name="TEST_DATASET", slug=dataset_slug, dataset_id=1)


@pytest.fixture
def remote_dataset_v2(team_slug: str, dataset_slug: str, local_config_file: Config):
    client = Client(local_config_file)
    return RemoteDatasetV2(client=client, team=team_slug, name="TEST_DATASET", slug=dataset_slug, dataset_id=1)


@pytest.fixture
def dataset_identifier(team_slug: str, dataset_slug: str):
    return f"{team_slug}/{dataset_slug}"


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
    def raises_if_status_not_supported(dataset_identifier: str):
        with pytest.raises(SystemExit) as exception:
            set_file_status(dataset_identifier, "unknown", [])
            assert exception.value.code == 1

    def calls_dataset_archive(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV1, "archive") as mock:
                    set_file_status(dataset_identifier, "archived", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def calls_dataset_clear(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV1, "reset") as mock:
                    set_file_status(dataset_identifier, "clear", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def calls_dataset_new(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV1, "move_to_new") as mock:
                    set_file_status(dataset_identifier, "new", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)

    def calls_dataset_restore_archived(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV1, "restore_archived") as mock:
                    set_file_status(dataset_identifier, "restore-archived", ["one.jpg", "two.jpg"])
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": "one.jpg,two.jpg"})
                    mock.assert_called_once_with(fetch_remote_files_mock.return_value)


def describe_delete_files():
    def test_bypasses_user_prompt_if_yes_flag_is_true(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(RemoteDatasetV1, "delete_items") as mock:
                    delete_files(dataset_identifier, ["one.jpg", "two.jpg"], True)
                    get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                    fetch_remote_files_mock.assert_called_once_with({"filenames": ["one.jpg", "two.jpg"]})
                    mock.assert_called_once()

    def test_deletes_items_if_user_accepts_prompt(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(builtins, "input", lambda _: "y"):
                    with patch.object(RemoteDatasetV1, "delete_items") as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"])
                        get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                        fetch_remote_files_mock.assert_called_once_with({"filenames": ["one.jpg", "two.jpg"]})
                        mock.assert_called_once()

    def test_does_not_delete_items_if_user_refuses_prompt(dataset_identifier: str, remote_dataset: RemoteDataset):
        with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
            with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                with patch.object(builtins, "input", lambda _: "n"):
                    with patch.object(RemoteDatasetV1, "delete_items") as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"])
                        get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                        fetch_remote_files_mock.assert_called_once_with({"filenames": ["one.jpg", "two.jpg"]})
                        mock.assert_not_called()

    def test_exits_if_error_occurs(dataset_identifier: str, remote_dataset: RemoteDataset):
        def error_mock():
            raise ValueError("Something went Wrong")

        with patch.object(sys, "exit") as exception:
            with patch.object(Client, "get_remote_dataset", return_value=remote_dataset) as get_remote_dataset_mock:
                with patch.object(RemoteDatasetV1, "fetch_remote_files") as fetch_remote_files_mock:
                    with patch.object(RemoteDatasetV1, "delete_items", side_effect=error_mock) as mock:
                        delete_files(dataset_identifier, ["one.jpg", "two.jpg"], True)

                        get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
                        fetch_remote_files_mock.assert_called_once_with({"filenames": ["one.jpg", "two.jpg"]})
                        mock.assert_called_once()
                        exception.assert_called_once_with(1)


def describe_benchmarks():
    def happy_path(dataset_identifier: str, remote_dataset_v2: RemoteDataset):
        ground_truth_id = str(uuid.uuid4())
        predictions_annotation_group_id = str(uuid.uuid4())

        with patch.object(Client, "feature_enabled", return_value=True), patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset_v2
        ) as get_remote_dataset_mock, patch.object(
            darwin.cli_functions,
            "import_annotations",
            return_value=ImportResult(finished=True, annotation_group_id=predictions_annotation_group_id),
        ) as import_annotations_mock, patch.object(
            remote_dataset_v2, "get_or_create_ground_truth", return_value=ground_truth_id
        ) as get_or_create_ground_truth_mock, patch.object(
            remote_dataset_v2, "begin_evaluation_run"
        ) as begin_evaluation_run_mock:
            paths: List[Union[str, Path]] = ["/tmp/foo", "/tmp/bar"]
            begin_evaluation_run(dataset_identifier, "My Run", paths, "darwin")

            get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
            import_annotations_mock.assert_called_once_with(
                remote_dataset_v2,
                darwin.importer.formats.darwin.parse_path,
                paths,
                append=True,
                to_new_annotation_group=True,
                import_annotators=True,
                import_reviewers=True,
            )
            get_or_create_ground_truth_mock.assert_called_once()
            begin_evaluation_run_mock.assert_called_once_with(
                ground_truth_id, predictions_annotation_group_id, "My Run"
            )

    def stops_if_feature_is_disabled(dataset_identifier: str, remote_dataset_v2: RemoteDataset):
        ground_truth_id = str(uuid.uuid4())
        predictions_annotation_group_id = str(uuid.uuid4())

        with patch.object(Client, "feature_enabled", return_value=False), patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset_v2
        ) as get_remote_dataset_mock, patch.object(
            darwin.cli_functions,
            "import_annotations",
            return_value=ImportResult(finished=True, annotation_group_id=predictions_annotation_group_id),
        ) as import_annotations_mock, patch.object(
            remote_dataset_v2, "get_or_create_ground_truth", return_value=ground_truth_id
        ) as get_or_create_ground_truth_mock, patch.object(
            remote_dataset_v2, "begin_evaluation_run"
        ) as begin_evaluation_run_mock, patch.object(
            sys, "exit"
        ) as sys_exit_mock:
            paths: List[Union[str, Path]] = ["/tmp/foo", "/tmp/bar"]
            begin_evaluation_run(dataset_identifier, "My Run", paths, "darwin")

            sys_exit_mock.assert_called_once()

            get_remote_dataset_mock.assert_not_called()
            import_annotations_mock.assert_not_called()
            get_or_create_ground_truth_mock.assert_not_called()
            begin_evaluation_run_mock.assert_not_called()

    def stops_if_dataset_not_found(dataset_identifier: str, remote_dataset_v2: RemoteDataset):
        def raise_not_found(dataset_identifier):
            raise NotFound(dataset_identifier)

        ground_truth_id = str(uuid.uuid4())
        predictions_annotation_group_id = str(uuid.uuid4())

        with patch.object(Client, "feature_enabled", return_value=True), patch.object(
            Client, "get_remote_dataset", side_effect=raise_not_found
        ) as get_remote_dataset_mock, patch.object(
            darwin.cli_functions,
            "import_annotations",
            return_value=ImportResult(finished=True, annotation_group_id=predictions_annotation_group_id),
        ) as import_annotations_mock, patch.object(
            remote_dataset_v2, "get_or_create_ground_truth", return_value=ground_truth_id
        ) as get_or_create_ground_truth_mock, patch.object(
            remote_dataset_v2, "begin_evaluation_run"
        ) as begin_evaluation_run_mock, patch.object(
            sys, "exit"
        ) as sys_exit_mock:
            paths: List[Union[str, Path]] = ["/tmp/foo", "/tmp/bar"]
            begin_evaluation_run(dataset_identifier, "My Run", paths, "darwin")

            sys_exit_mock.assert_called_once()
            get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)

            import_annotations_mock.assert_not_called()
            get_or_create_ground_truth_mock.assert_not_called()
            begin_evaluation_run_mock.assert_not_called()

    def stops_if_import_was_cancelled(dataset_identifier: str, remote_dataset_v2: RemoteDataset):
        ground_truth_id = str(uuid.uuid4())

        with patch.object(Client, "feature_enabled", return_value=True), patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset_v2
        ) as get_remote_dataset_mock, patch.object(
            darwin.cli_functions,
            "import_annotations",
            return_value=ImportResult(finished=False, annotation_group_id=None),
        ) as import_annotations_mock, patch.object(
            remote_dataset_v2, "get_or_create_ground_truth", return_value=ground_truth_id
        ) as get_or_create_ground_truth_mock, patch.object(
            remote_dataset_v2, "begin_evaluation_run"
        ) as begin_evaluation_run_mock, patch.object(
            sys, "exit"
        ) as sys_exit_mock:
            paths: List[Union[str, Path]] = ["/tmp/foo", "/tmp/bar"]
            begin_evaluation_run(dataset_identifier, "My Run", paths, "darwin")

            sys_exit_mock.assert_called_once()
            get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
            import_annotations_mock.assert_called_once_with(
                remote_dataset_v2,
                darwin.importer.formats.darwin.parse_path,
                paths,
                append=True,
                to_new_annotation_group=True,
                import_annotators=True,
                import_reviewers=True,
            )

            get_or_create_ground_truth_mock.assert_not_called()
            begin_evaluation_run_mock.assert_not_called()

    def stops_if_import_fails(dataset_identifier: str, remote_dataset_v2: RemoteDataset):
        def raise_import_error(*args, **kwargs):
            raise UnknownAnnotationFileSchema(Path("/tmp/foo"), [], dt.AnnotationFileVersion())

        ground_truth_id = str(uuid.uuid4())

        with patch.object(Client, "feature_enabled", return_value=True), patch.object(
            Client, "get_remote_dataset", return_value=remote_dataset_v2
        ) as get_remote_dataset_mock, patch.object(
            darwin.cli_functions, "import_annotations", side_effect=raise_import_error
        ) as import_annotations_mock, patch.object(
            remote_dataset_v2, "get_or_create_ground_truth", return_value=ground_truth_id
        ) as get_or_create_ground_truth_mock, patch.object(
            remote_dataset_v2, "begin_evaluation_run"
        ) as begin_evaluation_run_mock, patch.object(
            sys, "exit"
        ) as sys_exit_mock:
            paths: List[Union[str, Path]] = ["/tmp/foo", "/tmp/bar"]
            begin_evaluation_run(dataset_identifier, "My Run", paths, "darwin")

            sys_exit_mock.assert_called_once()
            get_remote_dataset_mock.assert_called_once_with(dataset_identifier=dataset_identifier)
            import_annotations_mock.assert_called_once_with(
                remote_dataset_v2,
                darwin.importer.formats.darwin.parse_path,
                paths,
                append=True,
                to_new_annotation_group=True,
                import_annotators=True,
                import_reviewers=True,
            )

            get_or_create_ground_truth_mock.assert_not_called()
            begin_evaluation_run_mock.assert_not_called()
