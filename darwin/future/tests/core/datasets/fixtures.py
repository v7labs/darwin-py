from unittest.mock import MagicMock

from pydantic import BaseModel, ValidationError
from pytest import fixture
from requests import HTTPError

from darwin.future.core.client import CoreClient


@fixture
def basic_dataset() -> dict:
    return {
        "name": "test-dataset",
        "slug": "1337",
        "id": 1,
        "releases": [],
    }


@fixture
def basic_list_of_datasets() -> list:
    return [
        {
            "name": "test-dataset",
            "slug": "1337",
            "id": 1,
            "releases": [],
        },
        {
            "name": "test-dataset-2",
            "slug": "1338",
            "id": 2,
            "releases": [],
        },
        {
            "name": "test-dataset-3",
            "slug": "1339",
            "id": 3,
            "releases": [],
        },
    ]


@fixture
def sad_http_client() -> CoreClient:
    mock = MagicMock(CoreClient)
    mock.post.side_effect = HTTPError("error")
    mock.get.side_effect = HTTPError("error")
    mock.delete.side_effect = HTTPError("error")

    return mock


@fixture
def happy_post_client() -> CoreClient:
    mock_client = MagicMock(CoreClient)
    mock_client.post.return_value = {
        "name": "test-dataset",
        "slug": "1337",
        "id": 1,
        "releases": [],
    }

    return mock_client


@fixture
def happy_get_client() -> CoreClient:
    mock_client = MagicMock(CoreClient)
    mock_client.get.return_value = [
        {
            "name": "test-dataset",
            "slug": "1337",
            "id": 1,
            "releases": [],
        }
    ]

    return mock_client


@fixture
def sad_client_pydantic() -> CoreClient:
    return MagicMock(CoreClient, side_effect=ValidationError(["error1", "error2", "error3"], model=BaseModel))
