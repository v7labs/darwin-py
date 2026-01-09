import builtins
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import call, patch

import pytest
import responses
from rich.console import Console

from darwin import cli
from darwin.cli_functions import (
    delete_files,
    extract_video_artifacts,
    pull_dataset,
    set_file_status,
    upload_data,
)
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.datatypes import AnnotatorReportGrouping
from darwin.options import Options
from darwin.utils import BLOCKED_UPLOAD_ERROR_ALREADY_EXISTS
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
        request_upload_response = {
            "blocked_items": [
                {
                    "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                    "name": "test_1.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_1.jpg",
                            "reason": BLOCKED_UPLOAD_ERROR_ALREADY_EXISTS,
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
            with patch.object(remote_dataset, "fetch_remote_files", return_value=[]):
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
                        call(
                            "Skipped 1 files already in the dataset.\n", style="warning"
                        )
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
        request_upload_response = {
            "blocked_items": [
                {
                    "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                    "name": "test_1.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "file_name": "test_1.jpg",
                            "reason": BLOCKED_UPLOAD_ERROR_ALREADY_EXISTS,
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
            with patch.object(remote_dataset, "fetch_remote_files", return_value=[]):
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
                        False,
                        True,
                    )
                    get_remote_dataset_mock.assert_called_once()

                    assert (
                        call(
                            "Skipped 1 files already in the dataset.\n", style="warning"
                        )
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
                        {"item_names": "one.jpg,two.jpg"}
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
                        {"item_names": "one.jpg,two.jpg"}
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
                        {"item_names": "one.jpg,two.jpg"}
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
                        {"item_names": ["one.jpg", "two.jpg"]}
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
                            {"item_names": ["one.jpg", "two.jpg"]}
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
                            {"item_names": ["one.jpg", "two.jpg"]}
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
                            {"item_names": ["one.jpg", "two.jpg"]}
                        )
                        mock.assert_called_once()
                        exception.assert_called_once_with(1)


class TestExtractVideo:
    def test_extract_video(self, tmp_path):
        """Test basic video extraction via CLI function"""
        source_file = "test_video.mp4"
        output_dir = str(tmp_path)

        with patch("darwin.extractor.video.extract_artifacts") as mock_extract:
            mock_extract.return_value = {}

            extract_video_artifacts(
                source_file,
                output_dir,
                storage_key_prefix="test/prefix",
                fps=30.0,
                segment_length=2,
                repair=False,
            )

            mock_extract.assert_called_once_with(
                source_file=source_file,
                output_dir=output_dir,
                fps=30.0,
                segment_length=2,
                repair=False,
                storage_key_prefix="test/prefix",
                save_metadata=True,
                extract_preview_frames=True,
                primary_frames_quality=1,
            )

    def test_extract_video_with_extract_preview_frames_false(self, tmp_path):
        """Test video extraction with extract_preview_frames=False"""
        source_file = "test_video.mp4"
        output_dir = str(tmp_path)

        with patch("darwin.extractor.video.extract_artifacts") as mock_extract:
            mock_extract.return_value = {}

            extract_video_artifacts(
                source_file,
                output_dir,
                storage_key_prefix="test/prefix",
                fps=30.0,
                segment_length=2,
                repair=False,
                extract_preview_frames=False,
            )

            mock_extract.assert_called_once_with(
                source_file=source_file,
                output_dir=output_dir,
                fps=30.0,
                segment_length=2,
                repair=False,
                storage_key_prefix="test/prefix",
                save_metadata=True,
                extract_preview_frames=False,
                primary_frames_quality=1,
            )

    def test_extract_video_with_primary_frames_quality(self, tmp_path):
        """Test video extraction with primary_frames_quality set"""
        source_file = "test_video.mp4"
        output_dir = str(tmp_path)

        with patch("darwin.extractor.video.extract_artifacts") as mock_extract:
            mock_extract.return_value = {}

            extract_video_artifacts(
                source_file,
                output_dir,
                storage_key_prefix="test/prefix",
                fps=30.0,
                segment_length=2,
                repair=False,
                primary_frames_quality=5,
            )

            mock_extract.assert_called_once_with(
                source_file=source_file,
                output_dir=output_dir,
                fps=30.0,
                segment_length=2,
                repair=False,
                storage_key_prefix="test/prefix",
                save_metadata=True,
                extract_preview_frames=True,
                primary_frames_quality=5,
            )

    def test_extract_video_with_both_new_parameters(self, tmp_path):
        """Test video extraction with both new parameters"""
        source_file = "test_video.mp4"
        output_dir = str(tmp_path)

        with patch("darwin.extractor.video.extract_artifacts") as mock_extract:
            mock_extract.return_value = {}

            extract_video_artifacts(
                source_file,
                output_dir,
                storage_key_prefix="test/prefix",
                fps=30.0,
                segment_length=2,
                repair=False,
                extract_preview_frames=False,
                primary_frames_quality=10,
            )

            mock_extract.assert_called_once_with(
                source_file=source_file,
                output_dir=output_dir,
                fps=30.0,
                segment_length=2,
                repair=False,
                storage_key_prefix="test/prefix",
                save_metadata=True,
                extract_preview_frames=False,
                primary_frames_quality=10,
            )


class TestPullDataset:
    def test_allows_override_team_when_it_mismatches_identifier_team(
        self, remote_dataset: RemoteDataset
    ):
        dataset_identifier = "old-team/test-dataset:xyz"
        override_team = "new-team"

        with (
            patch("darwin.cli_functions.os.getenv", return_value=None),
            patch("darwin.cli_functions.Config") as config_cls_mock,
            patch("darwin.cli_functions.Client.from_config") as from_config_mock,
        ):
            config_inst = config_cls_mock.return_value
            config_inst.get.return_value = "team_specific_key"

            client_mock = from_config_mock.return_value
            client_mock.get_remote_dataset.return_value = remote_dataset
            client_mock.newer_darwin_version = None

            with patch.object(remote_dataset, "get_release"):
                with patch.object(remote_dataset, "pull"):
                    pull_dataset(dataset_identifier, team=override_team)

            called_identifier = client_mock.get_remote_dataset.call_args.kwargs[
                "dataset_identifier"
            ]
            assert called_identifier.team_slug == override_team
            assert called_identifier.dataset_slug == "test-dataset"
            assert called_identifier.version == "xyz"

    def test_allows_override_team_when_it_matches_identifier_team(
        self, remote_dataset: RemoteDataset
    ):
        dataset_identifier = "old-team/test-dataset:xyz"
        override_team = "old-team"

        with (
            patch("darwin.cli_functions.os.getenv", return_value=None),
            patch("darwin.cli_functions.Config") as config_cls_mock,
            patch("darwin.cli_functions.Client.from_config") as from_config_mock,
        ):
            config_inst = config_cls_mock.return_value
            config_inst.get.return_value = "team_specific_key"

            client_mock = from_config_mock.return_value
            client_mock.get_remote_dataset.return_value = remote_dataset
            client_mock.newer_darwin_version = None

            with patch.object(remote_dataset, "get_release"):
                with patch.object(remote_dataset, "pull"):
                    pull_dataset(dataset_identifier, team=override_team)

            called_identifier = client_mock.get_remote_dataset.call_args.kwargs[
                "dataset_identifier"
            ]
            assert called_identifier.team_slug == override_team
            assert called_identifier.dataset_slug == "test-dataset"
            assert called_identifier.version == "xyz"

    def test_overrides_team_slug_no_team_in_identifier(
        self, remote_dataset: RemoteDataset
    ):
        dataset_identifier = "test-dataset:xyz"
        override_team = "new-team"

        with (
            patch("darwin.cli_functions.os.getenv", return_value=None),
            patch("darwin.cli_functions.Config") as config_cls_mock,
            patch("darwin.cli_functions.Client.from_config") as from_config_mock,
        ):
            config_inst = config_cls_mock.return_value
            config_inst.get.return_value = "team_specific_key"

            client_mock = from_config_mock.return_value
            client_mock.get_remote_dataset.return_value = remote_dataset
            client_mock.newer_darwin_version = None

            with patch.object(remote_dataset, "get_release"):
                with patch.object(remote_dataset, "pull"):
                    pull_dataset(dataset_identifier, team=override_team)

            # Verify get_remote_dataset was called with the overridden team
            called_identifier = client_mock.get_remote_dataset.call_args.kwargs[
                "dataset_identifier"
            ]
            assert called_identifier.team_slug == override_team
            assert called_identifier.dataset_slug == "test-dataset"
            assert called_identifier.version == "xyz"

    def test_uses_original_team_slug_if_no_override(
        self, remote_dataset: RemoteDataset
    ):
        dataset_identifier = "old-team/test-dataset:xyz"

        with (
            patch("darwin.cli_functions.os.getenv", return_value=None),
            patch("darwin.cli_functions.Config") as config_cls_mock,
            patch("darwin.cli_functions.Client.from_config") as from_config_mock,
        ):
            config_inst = config_cls_mock.return_value
            config_inst.get.return_value = "team_specific_key"

            client_mock = from_config_mock.return_value
            client_mock.get_remote_dataset.return_value = remote_dataset
            client_mock.newer_darwin_version = None

            with patch.object(remote_dataset, "get_release"):
                with patch.object(remote_dataset, "pull"):
                    pull_dataset(dataset_identifier)

            # Verify get_remote_dataset was called with the original team
            called_identifier = client_mock.get_remote_dataset.call_args.kwargs[
                "dataset_identifier"
            ]
            assert called_identifier.team_slug == "old-team"


class TestPullDatasetTeamAuthSelection:
    def test_pull_prefers_config_team_api_key_over_env_var_when_team_is_specified(
        self, remote_dataset: RemoteDataset
    ):
        """
        Regression (pull-only): when pulling from a specific team in a multi-team setup, prefer
        the config's team key even if DARWIN_API_KEY is set (which otherwise pins auth to one team).
        """
        dataset_identifier = "old-team/test-dataset:xyz"
        override_team = "new-team"

        with (
            patch("darwin.cli_functions.os.getenv", return_value="env_api_key"),
            patch("darwin.cli_functions.Config") as config_cls_mock,
            patch("darwin.cli_functions.Client.from_config") as from_config_mock,
            patch("darwin.cli_functions.Client.from_api_key") as from_api_key_mock,
        ):
            config_inst = config_cls_mock.return_value
            config_inst.get.return_value = "team_specific_key"

            client_mock = from_config_mock.return_value
            client_mock.get_remote_dataset.return_value = remote_dataset
            client_mock.newer_darwin_version = None

            with patch.object(remote_dataset, "get_release"):
                with patch.object(remote_dataset, "pull"):
                    pull_dataset(dataset_identifier, team=override_team)

            from_config_mock.assert_called()
            from_api_key_mock.assert_not_called()


class TestReportAnnotators:
    def test_parses_datetimes_and_comma_separated_lists(
        self, remote_dataset: RemoteDataset
    ):
        start_date = datetime(2024, 11, 4, tzinfo=timezone.utc)
        stop_date = datetime(2025, 5, 1, tzinfo=timezone(timedelta(hours=2)))
        group_by = [
            AnnotatorReportGrouping.STAGES,
            AnnotatorReportGrouping.ANNOTATORS,
            AnnotatorReportGrouping.DATASETS,
        ]
        dataset_id = remote_dataset.dataset_id
        test_args = [
            "darwin",
            "report",
            "annotators",
            "--start",
            "2024-11-04T00:00:00Z",
            "--stop",
            "2025-05-01T00:00:00+02:00",
            "--group-by",
            "  stages, annotators,datasets",
            "--datasets",
            remote_dataset.slug,
        ]

        with (
            patch.object(sys, "argv", test_args),
            patch.object(Client, "list_remote_datasets", return_value=[remote_dataset]),
            patch.object(Client, "get_annotators_report") as get_report_mock,
        ):
            args, parser = Options().parse_args()
            cli._run(args, parser)

            get_report_mock.assert_called_once_with(
                [dataset_id],
                start_date,
                stop_date,
                group_by,
            )

    def test_exits_with_error_if_dataset_not_found(
        self, remote_dataset: RemoteDataset, capsys
    ):
        test_args = [
            "darwin",
            "report",
            "annotators",
            "--start",
            "2024-11-04T00:00:00Z",
            "--stop",
            "2025-05-01T00:00:00+02:00",
            "--group-by",
            "stages,annotators,datasets",
            "--datasets",
            f"{remote_dataset.slug},non-existent-dataset",
        ]

        with (
            patch.object(sys, "argv", test_args),
            patch.object(Client, "list_remote_datasets", return_value=[remote_dataset]),
        ):
            args, parser = Options().parse_args()

            with pytest.raises(SystemExit):
                cli._run(args, parser)

            captured = capsys.readouterr()
            assert (
                "Error: Datasets '['non-existent-dataset']' do not exist."
                in captured.out
            )

    def test_raises_if_invalid_grouping_option_supplied(
        self, remote_dataset: RemoteDataset, capsys
    ):
        test_args = [
            "darwin",
            "report",
            "annotators",
            "--start",
            "2024-11-04T00:00:00Z",
            "--stop",
            "2025-05-01T00:00:00+02:00",
            "--group-by",
            "annotators,bad-grouping-option",
        ]

        with (
            patch.object(sys, "argv", test_args),
            patch.object(Client, "list_remote_datasets", return_value=[remote_dataset]),
        ):
            args, parser = Options().parse_args()

            with pytest.raises(
                ValueError,
                match="'bad-grouping-option' is not a valid AnnotatorReportGrouping",
            ):
                cli._run(args, parser)
