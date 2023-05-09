from unittest.mock import MagicMock

from pytest import fixture, raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.create_dataset import create_dataset


@fixture
def happy_client() -> Client:
    mock_client = MagicMock(Client)
    mock_client.post.return_value = {
        "name": "test-dataset",
        "slug": "1337",
        "id": 1,
        "releases": [],
    }

    return mock_client


@fixture
def sad_client() -> Client:
    error = HTTPError("Something went wrong")

    error.response.status_code = 400
    error.response.json = lambda: {"message": "Dataset name already taken"}

    raise error


def test_it_creates_a_dataset(happy_client: Client) -> None:
    dataset = create_dataset(happy_client, "test-dataset")
    assert dataset.name == "test-dataset"
    assert dataset.slug == "1337"


def it_raises_an_error_if_the_dataset_name_is_already_taken(sad_client: Client) -> None:
    with raises(HTTPError):
        create_dataset(sad_client, "test-dataset")
        create_dataset(sad_client, "test-dataset")
