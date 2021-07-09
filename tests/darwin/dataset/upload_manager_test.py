from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import responses
from darwin.client import Client
from darwin.config import Config
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.upload_manager import ItemPayload, UploadHandler
from tests.fixtures import *


@pytest.fixture
def darwin_client(darwin_config_path: Path, darwin_datasets_path: Path, team_slug: str) -> Client:
    config = Config(darwin_config_path)
    config.put(["global" , "api_endpoint"], "http://localhost/api/")
    config.put(["global" , "base_url"], "http://localhost")
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
def test_request_upload_is_called_on_init(darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str):
    response = {"blocked_items": [], "items": []}
    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)
    
    upload_handler = UploadHandler(darwin_client, [], dataset_identifier)
    
    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 0
    assert upload_handler.error_count == 0

    responses.assert_call_count(request_upload_endpoint, 1) is True

@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_pending_count_is_correct(darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str):
    response = {
        "blocked_items": [],
        "items": [
            {"dataset_item_id": 1, "filename": "test.jpg", "path": "/"}
        ]
    }

    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)
    
    upload_handler = UploadHandler(darwin_client, [], dataset_identifier)
    
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
def test_blocked_count_is_correct(darwin_client: Client, dataset_identifier: DatasetIdentifier, request_upload_endpoint: str):
    response = {
        "blocked_items": [
            {"dataset_item_id": 1, "filename": "test.jpg", "path": "/", "reason": "ALREADY_EXISTS"}
        ],
        "items": []
    }

    responses.add(responses.PUT, request_upload_endpoint, json=response, status=200)
    
    upload_handler = UploadHandler(darwin_client, [], dataset_identifier)
    
    assert upload_handler.pending_count == 0
    assert upload_handler.blocked_count == 1
    assert upload_handler.error_count == 0

    blocked_item = upload_handler.blocked_items[0]

    assert blocked_item.dataset_item_id == 1
    assert blocked_item.filename == "test.jpg"
    assert blocked_item.path == "/"
    assert blocked_item.reason == "ALREADY_EXISTS"
