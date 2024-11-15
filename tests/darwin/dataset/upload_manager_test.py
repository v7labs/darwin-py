from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses
import inspect


from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.dataset.upload_manager import (
    LocalFile,
    UploadHandler,
    UploadHandlerV2,
    UploadStage,
    _upload_chunk_size,
)
from tests.fixtures import *
from darwin.utils import BLOCKED_UPLOAD_ERROR_ALREADY_EXISTS


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
    return Client(config=config)


@pytest.fixture
def dataset_identifier(team_slug: str, dataset_slug: str) -> DatasetIdentifier:
    return DatasetIdentifier(dataset_slug=dataset_slug, team_slug=team_slug)


@pytest.fixture
def request_upload_endpoint(team_slug_darwin_json_v2: str):
    return f"http://localhost/api/v2/teams/{team_slug_darwin_json_v2}/items/register_upload"


@pytest.fixture
def dataset(
    darwin_client: Client, team_slug_darwin_json_v2: str, dataset_slug: str
) -> RemoteDataset:
    return RemoteDatasetV2(
        client=darwin_client,
        team=team_slug_darwin_json_v2,
        name=dataset_slug,
        slug=dataset_slug,
        dataset_id=1,
    )


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_request_upload_is_not_called_on_init(
    dataset: RemoteDataset, request_upload_endpoint: str
):
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        with patch.object(
            UploadHandler, "skip_existing_full_remote_filepaths", return_value=[]
        ):
            upload_handler = UploadHandler.build(dataset, [])

    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 0
    assert upload_handler.error_count == 0

    responses.assert_call_count(request_upload_endpoint, 0)


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_pending_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.jpg",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "as_frames": False,
                        "extract_views": False,
                    }
                ],
            }
        ],
    }

    responses.add(responses.POST, request_upload_endpoint, json=response, status=200)

    local_file = LocalFile(local_path=Path("test.jpg"))
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        upload_handler = UploadHandler.build(dataset, [local_file])

    assert upload_handler.pending_count == 1
    assert upload_handler.blocked_count == 0
    assert upload_handler.error_count == 0

    pending_item = upload_handler.pending_items[0]

    assert pending_item.dataset_item_id == "3b241101-e2bb-4255-8caf-4136c566a964"
    assert pending_item.filename == "test.jpg"
    assert pending_item.path == "/"
    assert pending_item.slots[0].reason is None


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_blocked_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    response = {
        "blocked_items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.jpg",
                        "reason": BLOCKED_UPLOAD_ERROR_ALREADY_EXISTS,
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "as_frames": False,
                        "extract_views": False,
                    }
                ],
            }
        ],
        "items": [],
    }

    responses.add(responses.POST, request_upload_endpoint, json=response, status=200)

    local_file = LocalFile(local_path=Path("test.jpg"))
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        upload_handler = UploadHandler.build(dataset, [local_file])

    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 1
    assert upload_handler.error_count == 0

    blocked_item = upload_handler.blocked_items[0]

    assert blocked_item.dataset_item_id == "3b241101-e2bb-4255-8caf-4136c566a964"
    assert blocked_item.filename == "test.jpg"
    assert blocked_item.path == "/"
    assert blocked_item.slots[0].reason == BLOCKED_UPLOAD_ERROR_ALREADY_EXISTS


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_error_count_is_correct_on_signature_request(
    dataset: RemoteDataset, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.jpg",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "as_frames": False,
                        "extract_views": False,
                    }
                ],
            }
        ],
    }
    upload_to_s3_endpoint = (
        "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    )
    confirm_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/confirm"
    sign_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/sign"

    responses.add(
        responses.POST,
        request_upload_endpoint,
        json=request_upload_response,
        status=200,
    )
    responses.add(responses.GET, sign_upload_endpoint, status=500)

    local_file = LocalFile(local_path=Path("test.jpg"))
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        upload_handler = UploadHandler.build(dataset, [local_file])

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1)
    responses.assert_call_count(sign_upload_endpoint, 1)
    responses.assert_call_count(upload_to_s3_endpoint, 0)
    responses.assert_call_count(confirm_upload_endpoint, 0)

    assert upload_handler.pending_count == 1
    assert upload_handler.error_count == 1
    assert upload_handler.blocked_count == 0

    error = upload_handler.errors[0]
    assert str(error.file_path) == "test.jpg"
    assert error.stage == UploadStage.REQUEST_SIGNATURE


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_error_count_is_correct_on_upload_to_s3(
    dataset: RemoteDataset, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.jpg",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "as_frames": False,
                        "extract_views": False,
                    }
                ],
            }
        ],
    }

    upload_to_s3_endpoint = (
        "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    )
    confirm_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/confirm"
    sign_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/sign"
    sign_upload_response = {"upload_url": upload_to_s3_endpoint}

    responses.add(
        responses.POST,
        request_upload_endpoint,
        json=request_upload_response,
        status=200,
    )
    responses.add(
        responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200
    )
    responses.add(responses.PUT, upload_to_s3_endpoint, status=500)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path=Path("test.jpg"))
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        upload_handler = UploadHandler.build(dataset, [local_file])

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1)
    responses.assert_call_count(sign_upload_endpoint, 1)
    responses.assert_call_count(upload_to_s3_endpoint, 1)
    responses.assert_call_count(confirm_upload_endpoint, 0)

    assert upload_handler.pending_count == 1
    assert upload_handler.error_count == 1
    assert upload_handler.blocked_count == 0

    error = upload_handler.errors[0]
    assert str(error.file_path) == "test.jpg"
    assert error.stage == UploadStage.UPLOAD_TO_S3


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_error_count_is_correct_on_confirm_upload(
    dataset: RemoteDataset, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.jpg",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "as_frames": False,
                        "extract_views": False,
                    }
                ],
            }
        ],
    }

    upload_to_s3_endpoint = (
        "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    )
    confirm_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/confirm"
    sign_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/sign"
    sign_upload_response = {"upload_url": upload_to_s3_endpoint}

    responses.add(
        responses.POST,
        request_upload_endpoint,
        json=request_upload_response,
        status=200,
    )
    responses.add(
        responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200
    )
    responses.add(responses.PUT, upload_to_s3_endpoint, status=201)
    responses.add(responses.PUT, confirm_upload_endpoint, status=500)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path=Path("test.jpg"))
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        upload_handler = UploadHandler.build(dataset, [local_file])

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1)
    responses.assert_call_count(sign_upload_endpoint, 1)
    responses.assert_call_count(upload_to_s3_endpoint, 1)
    responses.assert_call_count(confirm_upload_endpoint, 1)

    assert upload_handler.pending_count == 1
    assert upload_handler.error_count == 1
    assert upload_handler.blocked_count == 0

    error = upload_handler.errors[0]
    assert str(error.file_path) == "test.jpg"
    assert error.stage == UploadStage.CONFIRM_UPLOAD_COMPLETE


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_upload_files(dataset: RemoteDataset, request_upload_endpoint: str):
    request_upload_response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.jpg",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
                        "as_frames": False,
                        "extract_views": False,
                    }
                ],
            }
        ],
    }

    upload_to_s3_endpoint = (
        "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    )
    confirm_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/confirm"
    sign_upload_endpoint = "http://localhost/api/v2/teams/v7-darwin-json-v2/items/uploads/123e4567-e89b-12d3-a456-426614174000/sign"
    sign_upload_response = {"upload_url": upload_to_s3_endpoint}

    responses.add(
        responses.POST,
        request_upload_endpoint,
        json=request_upload_response,
        status=200,
    )
    responses.add(
        responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200
    )
    responses.add(responses.PUT, upload_to_s3_endpoint, status=201)
    responses.add(responses.POST, confirm_upload_endpoint, status=200)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path=Path("test.jpg"))
    with patch.object(dataset, "fetch_remote_files", return_value=[]):
        upload_handler = UploadHandler.build(dataset, [local_file])

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1)
    responses.assert_call_count(sign_upload_endpoint, 1)
    responses.assert_call_count(upload_to_s3_endpoint, 1)
    responses.assert_call_count(confirm_upload_endpoint, 1)

    assert upload_handler.error_count == 0


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_upload_files_adds_handle_as_slices_option_to_upload_payload(
    dataset: RemoteDataset, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.dcm",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.dcm",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
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
    Path("test.dcm").touch()
    local_file = LocalFile(local_path=Path("test.dcm"))
    with patch("darwin.backend_v2.BackendV2.register_data") as mock_register_data:
        with patch.object(dataset, "fetch_remote_files", return_value=[]):
            UploadHandler.build(dataset, [local_file], handle_as_slices=True)
            assert mock_register_data.call_count == 1
            assert mock_register_data.call_args[0][1]["options"] == {
                "handle_as_slices": True
            }


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_upload_files_does_not_add_handle_as_slices_option_to_upload_payload(
    dataset: RemoteDataset, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [
            {
                "id": "3b241101-e2bb-4255-8caf-4136c566a964",
                "name": "test.dcm",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "file_name": "test.dcm",
                        "slot_name": "0",
                        "upload_id": "123e4567-e89b-12d3-a456-426614174000",
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
    Path("test.dcm").touch()
    local_file = LocalFile(local_path=Path("test.dcm"))
    with patch("darwin.backend_v2.BackendV2.register_data") as mock_register_data:
        with patch.object(dataset, "fetch_remote_files", return_value=[]):
            UploadHandler.build(dataset, [local_file], handle_as_slices=False)
            assert mock_register_data.call_count == 1
            assert mock_register_data.call_args[0][1]["options"] == {
                "handle_as_slices": False
            }


def test_default_value_for_handle_as_slices():
    signature = inspect.signature(UploadHandlerV2._request_upload)
    handle_as_slices_default_value = signature.parameters["handle_as_slices"].default
    assert handle_as_slices_default_value is False


class TestUploadChunkSize:

    def test_default_value_when_env_var_is_not_set(self):
        assert _upload_chunk_size() == 500

    @patch("os.getenv", return_value="hello")
    def test_default_value_when_env_var_is_not_integer(self, mock: MagicMock):
        assert _upload_chunk_size() == 500
        mock.assert_called_once_with("DARWIN_UPLOAD_CHUNK_SIZE")

    @patch("os.getenv", return_value="123")
    def test_value_specified_by_env_var(self, mock: MagicMock):
        assert _upload_chunk_size() == 123
        mock.assert_called_once_with("DARWIN_UPLOAD_CHUNK_SIZE")


def test_skip_existing_full_remote_filepaths_with_local_files():
    mock_dataset = MagicMock()
    mock_dataset.fetch_remote_files.return_value = [
        MagicMock(full_path="/existing_file_1.jpg"),
        MagicMock(full_path="/existing_file_2.jpg"),
    ]
    mock_dataset.slug = "test-dataset"

    local_file_1 = MagicMock(full_path="/existing_file_1.jpg")
    local_file_2 = MagicMock(full_path="/new_file.jpg")

    with patch("darwin.dataset.upload_manager.Console.print") as mock_print:
        upload_handler = UploadHandlerV2(mock_dataset, [local_file_1, local_file_2], [])

        assert local_file_1 not in upload_handler.local_files
        assert local_file_2 in upload_handler.local_files

        mock_print.assert_any_call(
            "The remote filepath /existing_file_1.jpg already exists in the `test-dataset` dataset. Skipping upload of item.",
            style="warning",
        )


def test_skip_existing_full_remote_filepaths_with_multi_file_items():
    mock_dataset = MagicMock()
    mock_dataset.fetch_remote_files.return_value = [
        MagicMock(full_path="/existing_multi_file_item.jpg"),
    ]
    mock_dataset.slug = "test-dataset"

    multi_file_item_1 = MagicMock(
        full_path="/existing_multi_file_item.jpg", files=[MagicMock()]
    )
    multi_file_item_2 = MagicMock(
        full_path="/new_multi_file_item.jpg", files=[MagicMock()]
    )

    with patch("darwin.dataset.upload_manager.Console.print") as mock_print:
        upload_handler = UploadHandlerV2(
            mock_dataset, [], [multi_file_item_1, multi_file_item_2]
        )

        assert multi_file_item_1 not in upload_handler.multi_file_items
        assert multi_file_item_2 in upload_handler.multi_file_items

        # Verify that the correct warning was printed
        mock_print.assert_any_call(
            "The remote filepath /existing_multi_file_item.jpg is already occupied by a dataset item in the `test-dataset` dataset. Skipping upload of item.",
            style="warning",
        )


def test_skip_existing_full_remote_filepaths_raises_if_no_files_left():
    mock_dataset = MagicMock()
    mock_dataset.fetch_remote_files.return_value = [
        MagicMock(full_path="/existing_multi_file_item_1.jpg"),
        MagicMock(full_path="/existing_multi_file_item_2.jpg"),
    ]
    mock_dataset.slug = "test-dataset"

    multi_file_item_1 = MagicMock(
        full_path="/existing_multi_file_item_1.jpg", files=[MagicMock()]
    )
    multi_file_item_2 = MagicMock(
        full_path="/existing_multi_file_item_2.jpg", files=[MagicMock()]
    )

    with pytest.raises(
        ValueError,
        match="All items to be uploaded have paths that already exist in the remote dataset. No items to upload.",
    ):
        UploadHandlerV2(mock_dataset, [], [multi_file_item_1, multi_file_item_2])
