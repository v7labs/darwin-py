from unittest.mock import MagicMock

from pydantic import BaseModel, ValidationError
from pytest import fixture
from requests import HTTPError

from darwin.future.core.client import Client


@fixture
def sad_http_client() -> Client:
    mock = MagicMock(Client)
    mock.post.side_effect = HTTPError("error")
    mock.get.side_effect = HTTPError("error")
    mock.delete.side_effect = HTTPError("error")

    return mock


@fixture
def happy_post_client() -> Client:
    mock_client = MagicMock(Client)
    mock_client.post.return_value = {
        "name": "test-dataset",
        "slug": "1337",
        "id": 1,
        "releases": [],
    }

    return mock_client


@fixture
def happy_get_client() -> Client:
    mock_client = MagicMock(Client)
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
def sad_client_pydantic() -> Client:
    return MagicMock(Client, side_effect=ValidationError(["error1", "error2", "error3"], model=BaseModel))
