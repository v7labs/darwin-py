from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from requests.exceptions import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.data_objects.dataset import Dataset


@pytest.fixture
def happy_client() -> Client:
    mock_client = MagicMock(Client)
    mock_client.post.return_value = [
        {
            "name": "test-dataset",
            "slug": "1337",
            "id": 1,
            "releases": [],
        }
    ]

    return mock_client


@pytest.fixture
def sad_client_http() -> Client:
    error = HTTPError("Something went wrong")

    error.response.status_code = 400
    error.response.json = lambda: {"message": "Dataset name already taken"}

    raise error


@pytest.fixture
def sad_client_pydantic() -> Client:
    error = ValidationError(
        errors=[
            "error1",
            "error2",
            "error3",
        ],
        model=Dataset,
    )

    raise error


def test_it_lists_datasets(happy_client: Client) -> None:
    with patch("darwin.client.Client.get") as mock_get:
        mock_get.return_value = [
            {
                "name": "test-dataset",
                "slug": "1337",
                "id": 1,
                "releases": [],
            }
        ]

        datasets = list_datasets(happy_client)

        assert len(datasets) == 1

        assert datasets[0].name == "test-dataset"
        assert datasets[0].slug == "1337"
