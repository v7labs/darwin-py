from pydantic import ValidationError
from pytest import raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.get_dataset import get_dataset

from .fixtures import happy_get_client, sad_client_pydantic, sad_http_client


def test_it_gets_a_dataset(happy_get_client: Client) -> None:
    happy_get_client.get.return_value = {  # type: ignore
        "name": "test-dataset",
        "slug": "1337",
        "id": 1,
        "releases": [],
    }

    dataset = get_dataset(happy_get_client, "test-dataset")

    assert dataset.name == "test-dataset"
    assert dataset.slug == "1337"


def test_it_raises_an_error_on_http_error(sad_http_client: Client) -> None:
    with raises(HTTPError):
        get_dataset(sad_http_client, "test-dataset")
        get_dataset(sad_http_client, "test-dataset")


def test_it_raises_an_error_on_pydantic_error(sad_client_pydantic: Client) -> None:
    with raises(ValidationError):
        get_dataset(sad_client_pydantic, "test-dataset")
        get_dataset(sad_client_pydantic, "test-dataset")
