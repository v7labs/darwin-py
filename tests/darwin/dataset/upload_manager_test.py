from pathlib import Path

import pytest
import responses
from darwin.client import Client
from darwin.config import Config
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.upload_manager import (
    LocalFile,
    UploadHandler,
    UploadRequestError,
    UploadStage,
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


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_request_upload_is_called_on_init(
    darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str
):
    response = {"blocked_items": [], "items": []}
    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)

    upload_handler = UploadHandler(darwin_client, [], dataset_identifier)

    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 0
    assert upload_handler.error_count == 0

    responses.assert_call_count(request_upload_endpoint, 1) is True


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_pending_count_is_correct(
    darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str
):
    response = {"blocked_items": [], "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}]}

    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)

    local_file = LocalFile(local_path="test.jpg")
    upload_handler = UploadHandler(darwin_client, [local_file], dataset_identifier)

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
def test_blocked_count_is_correct(
    darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str
):
    response = {
        "blocked_items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/", "reason": "ALREADY_EXISTS"}],
        "items": [],
    }

    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)

    local_file = LocalFile(local_path="test.jpg")
    upload_handler = UploadHandler(darwin_client, [local_file], dataset_identifier)

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
def test_error_count_is_correct(
    darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    upload_to_s3_endpoint = "http://s3-eu-west-1.amazonaws.com/bucket"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, status=500)

    local_file = LocalFile(local_path="test.jpg")
    upload_handler = UploadHandler(darwin_client, [local_file], dataset_identifier)

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1) is True
    responses.assert_call_count(sign_upload_endpoint, 1) is True
    responses.assert_call_count(upload_to_s3_endpoint, 0) is True
    responses.assert_call_count(confirm_upload_endpoint, 0) is True

    assert upload_handler.pending_count == 1
    assert upload_handler.error_count == 1
    assert upload_handler.blocked_count == 0

    error = upload_handler.errors[0]
    assert str(error.file_path) == "test.jpg"
    assert error.stage == UploadStage.REQUEST_SIGNATURE


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_error_count_is_correct(
    darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    sign_upload_response = {
        "postEndpoint": "//s3-eu-west-1.amazonaws.com/bucket",
        "signature": {
            "X-amz-algorithm": "AWS4-HMAC-SHA256",
            "X-amz-credential": "AAAAAAAAAAAAAAAAAAAA/20210630/eu-west-1/s3/aws4_request",
            "X-amz-date": "20210630T155613Z",
            "X-amz-signature": "b7cf89d35cf67322187086c542aa10fd39d4b6b661bf1111a05f5263f9fcc353",
            "acl": "private",
            "key": "0/datasets/1/originals/00000001.jpg",
            "policy": "eyJjb25kaXRpb25zIjpbeyJIdWNrZXQiOiJncmFwaG90YXRlLWRldiJ9LHsiYWNsIjoicHJpdmF0ZSJ9LHsic3VjY2Vzc19hY3Rpb25fc3RhdHVzIjoiMjAxIn0sWyJzdGFydHMtd2l0aCIsIiRrZXkiLCIiXSx7IngtYW16LWNyZWRlbnRpYWwiOiJBS0lBSVFKSDNJWEhHQ1M2TUJCQS8yMDIxMDYzMC9ldS13ZXN0LTIvczMvYXdzNF9yZXF1ZXN0In0seyJ4LWFtei1hbGdvcml0aG0iOiJBV1M0LUhNQUMtU0hBMjU2In0seyJ4LWFtei1kYXRlIjoiMjAyMTA2MzBUMTU1NjEzWiJ9XSwiZXhwaXJhdGlvbiI6IjIwMjEtMDctMDFUMTU6NTY6MTMuMDAwWiJ9",
            "success_action_status": "201",
        },
    }

    upload_to_s3_endpoint = "http://s3-eu-west-1.amazonaws.com/bucket"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200)
    responses.add(responses.POST, upload_to_s3_endpoint, content_type="multipart/form-data", status=500)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path="test.jpg")
    upload_handler = UploadHandler(darwin_client, [local_file], dataset_identifier)

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1) is True
    responses.assert_call_count(sign_upload_endpoint, 1) is True
    responses.assert_call_count(upload_to_s3_endpoint, 1) is True
    responses.assert_call_count(confirm_upload_endpoint, 0) is True

    assert upload_handler.pending_count == 1
    assert upload_handler.error_count == 1
    assert upload_handler.blocked_count == 0

    error = upload_handler.errors[0]
    assert str(error.file_path) == "test.jpg"
    assert error.stage == UploadStage.UPLOAD_TO_S3


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_error_count_is_correct(
    darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str
):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    sign_upload_response = {
        "postEndpoint": "//s3-eu-west-1.amazonaws.com/bucket",
        "signature": {
            "X-amz-algorithm": "AWS4-HMAC-SHA256",
            "X-amz-credential": "AAAAAAAAAAAAAAAAAAAA/20210630/eu-west-1/s3/aws4_request",
            "X-amz-date": "20210630T155613Z",
            "X-amz-signature": "b7cf89d35cf67322187086c542aa10fd39d4b6b661bf1111a05f5263f9fcc353",
            "acl": "private",
            "key": "0/datasets/1/originals/00000001.jpg",
            "policy": "eyJjb25kaXRpb25zIjpbeyJIdWNrZXQiOiJncmFwaG90YXRlLWRldiJ9LHsiYWNsIjoicHJpdmF0ZSJ9LHsic3VjY2Vzc19hY3Rpb25fc3RhdHVzIjoiMjAxIn0sWyJzdGFydHMtd2l0aCIsIiRrZXkiLCIiXSx7IngtYW16LWNyZWRlbnRpYWwiOiJBS0lBSVFKSDNJWEhHQ1M2TUJCQS8yMDIxMDYzMC9ldS13ZXN0LTIvczMvYXdzNF9yZXF1ZXN0In0seyJ4LWFtei1hbGdvcml0aG0iOiJBV1M0LUhNQUMtU0hBMjU2In0seyJ4LWFtei1kYXRlIjoiMjAyMTA2MzBUMTU1NjEzWiJ9XSwiZXhwaXJhdGlvbiI6IjIwMjEtMDctMDFUMTU6NTY6MTMuMDAwWiJ9",
            "success_action_status": "201",
        },
    }

    upload_to_s3_endpoint = "http://s3-eu-west-1.amazonaws.com/bucket"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200)
    responses.add(responses.POST, upload_to_s3_endpoint, content_type="multipart/form-data", status=201)
    responses.add(responses.PUT, confirm_upload_endpoint, status=500)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path="test.jpg")
    upload_handler = UploadHandler(darwin_client, [local_file], dataset_identifier)

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1) is True
    responses.assert_call_count(sign_upload_endpoint, 1) is True
    responses.assert_call_count(upload_to_s3_endpoint, 1) is True
    responses.assert_call_count(confirm_upload_endpoint, 1) is True

    assert upload_handler.pending_count == 1
    assert upload_handler.error_count == 1
    assert upload_handler.blocked_count == 0

    error = upload_handler.errors[0]
    assert str(error.file_path) == "test.jpg"
    assert error.stage == UploadStage.CONFIRM_UPLOAD_COMPLETE


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_upload_files(darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str):
    request_upload_response = {
        "blocked_items": [],
        "items": [{"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}],
    }

    sign_upload_endpoint = "http://localhost/api/dataset_items/1/sign_upload"
    sign_upload_response = {
        "postEndpoint": "//s3-eu-west-1.amazonaws.com/bucket",
        "signature": {
            "X-amz-algorithm": "AWS4-HMAC-SHA256",
            "X-amz-credential": "AAAAAAAAAAAAAAAAAAAA/20210630/eu-west-1/s3/aws4_request",
            "X-amz-date": "20210630T155613Z",
            "X-amz-signature": "b7cf89d35cf67322187086c542aa10fd39d4b6b661bf1111a05f5263f9fcc353",
            "acl": "private",
            "key": "0/datasets/1/originals/00000001.jpg",
            "policy": "eyJjb25kaXRpb25zIjpbeyJIdWNrZXQiOiJncmFwaG90YXRlLWRldiJ9LHsiYWNsIjoicHJpdmF0ZSJ9LHsic3VjY2Vzc19hY3Rpb25fc3RhdHVzIjoiMjAxIn0sWyJzdGFydHMtd2l0aCIsIiRrZXkiLCIiXSx7IngtYW16LWNyZWRlbnRpYWwiOiJBS0lBSVFKSDNJWEhHQ1M2TUJCQS8yMDIxMDYzMC9ldS13ZXN0LTIvczMvYXdzNF9yZXF1ZXN0In0seyJ4LWFtei1hbGdvcml0aG0iOiJBV1M0LUhNQUMtU0hBMjU2In0seyJ4LWFtei1kYXRlIjoiMjAyMTA2MzBUMTU1NjEzWiJ9XSwiZXhwaXJhdGlvbiI6IjIwMjEtMDctMDFUMTU6NTY6MTMuMDAwWiJ9",
            "success_action_status": "201",
        },
    }

    upload_to_s3_endpoint = "http://s3-eu-west-1.amazonaws.com/bucket"
    confirm_upload_endpoint = "http://localhost/api/dataset_items/1/confirm_upload"

    responses.add(responses.PUT, request_upload_endpoint, json=request_upload_response, status=200)
    responses.add(responses.GET, sign_upload_endpoint, json=sign_upload_response, status=200)
    responses.add(responses.POST, upload_to_s3_endpoint, content_type="multipart/form-data", status=201)
    responses.add(responses.PUT, confirm_upload_endpoint, status=200)

    Path("test.jpg").touch()
    local_file = LocalFile(local_path="test.jpg")
    upload_handler = UploadHandler(darwin_client, [local_file], dataset_identifier)

    upload_handler.upload()
    for file_to_upload in upload_handler.progress:
        file_to_upload()

    responses.assert_call_count(request_upload_endpoint, 1) is True
    responses.assert_call_count(sign_upload_endpoint, 1) is True
    responses.assert_call_count(upload_to_s3_endpoint, 1) is True
    responses.assert_call_count(confirm_upload_endpoint, 1) is True

    assert upload_handler.error_count == 0
