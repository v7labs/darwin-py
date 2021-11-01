from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.upload_manager import (
    LocalFile,
    UploadHandler,
    UploadStage,
    _upload_chunk_size,
)
from tests.fixtures import *


@pytest.fixture
def darwin_client(darwin_config_path: Path, darwin_datasets_path: Path, team_slug: str) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug, "api_key"], "mock_api_key")
    config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
    return Client(config)


@pytest.fixture
def dataset_identifier(team_slug: str, dataset_slug: str) -> DatasetIdentifier:
    return DatasetIdentifier(dataset_slug=dataset_slug, team_slug=team_slug)


@pytest.fixture
def request_upload_endpoint(team_slug: str, dataset_slug: str):
    return f"http://localhost/api/teams/{team_slug}/datasets/{dataset_slug}/data"


@pytest.fixture
def dataset(darwin_client: Client, team_slug: str, dataset_slug: str) -> RemoteDataset:
    return RemoteDataset(client=darwin_client, team=team_slug, name=dataset_slug, slug=dataset_slug, dataset_id=1)


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_request_upload_is_not_called_on_init(dataset: RemoteDataset, request_upload_endpoint: str):
    upload_handler = UploadHandler(dataset, [])

    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 0
    assert upload_handler.error_count == 0

    responses.assert_call_count(request_upload_endpoint, 0)


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_pending_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    response = {"blocked_items": [], "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}]}

    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)

    local_file = LocalFile(local_path=Path("test.jpg"))
    upload_handler = UploadHandler(dataset, [local_file])

    assert upload_handler.pending_count == 1
    assert upload_handler.blocked_count == 0
    assert upload_handler.error_count == 0

    pending_item = upload_handler.pending_items[0]

    assert pending_item.dataset_item_id == 1
    assert pending_item.filename == "test.jpg"
    assert pending_item.path == "/"
    assert pending_item.reason is None


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_blocked_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    response = {
        "blocked_items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/", "reason": "ALREADY_EXISTS"}],
        "items": [],
    }

    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)

    local_file = LocalFile(local_path=Path("test.jpg"))
    upload_handler = UploadHandler(dataset, [local_file])

    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 1
    assert upload_handler.error_count == 0

    blocked_item = upload_handler.blocked_items[0]

    assert blocked_item.dataset_item_id == 1
    assert blocked_item.filename == "test.jpg"
    assert blocked_item.path == "/"
    assert blocked_item.reason == "ALREADY_EXISTS"


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_error_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    upload_to_s3_endpoint = "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"

    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, status=500)

    local_file = LocalFile(local_path=Path("test.jpg"))
    upload_handler = UploadHandler(dataset, [local_file])

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
def test_error_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    upload_to_s3_endpoint = "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    sign_upload_response = {"upload_url": upload_to_s3_endpoint}

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200)
    responses.add(responses.PUT, upload_to_s3_endpoint, status=500)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path=Path("test.jpg"))
    upload_handler = UploadHandler(dataset, [local_file])

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
def test_error_count_is_correct(dataset: RemoteDataset, request_upload_endpoint: str):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    upload_to_s3_endpoint = "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    sign_upload_response = {"upload_url": upload_to_s3_endpoint}

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200)
    responses.add(responses.PUT, upload_to_s3_endpoint, status=201)
    responses.add(responses.PUT, confirm_upload_endpoint, status=500)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path=Path("test.jpg"))
    upload_handler = UploadHandler(dataset, [local_file])

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
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    upload_to_s3_endpoint = "https://darwin-data.s3.eu-west-1.amazonaws.com/test.jpg?X-Amz-Signature=abc"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    sign_upload_response = {"upload_url": upload_to_s3_endpoint}

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200)
    responses.add(responses.PUT, upload_to_s3_endpoint, status=201)
    responses.add(responses.PUT, confirm_upload_endpoint, status=200)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path=Path("test.jpg"))
    upload_handler = UploadHandler(dataset, [local_file])

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1)
    responses.assert_call_count(sign_upload_endpoint, 1)
    responses.assert_call_count(upload_to_s3_endpoint, 1)
    responses.assert_call_count(confirm_upload_endpoint, 1)

    assert upload_handler.error_count == 0


def describe_upload_chunk_size():
    def default_value_when_env_var_is_not_set():
        assert _upload_chunk_size() == 500

    @patch("os.getenv", return_value="hello")
    def default_value_when_env_var_is_not_integer(mock: MagicMock):
        assert _upload_chunk_size() == 500
        mock.assert_called_once_with("DARWIN_UPLOAD_CHUNK_SIZE")

    @patch("os.getenv", return_value="123")
    def value_specified_by_env_var(mock: MagicMock):
        assert _upload_chunk_size() == 123
        mock.assert_called_once_with("DARWIN_UPLOAD_CHUNK_SIZE")

