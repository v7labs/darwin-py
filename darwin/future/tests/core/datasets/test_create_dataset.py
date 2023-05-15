from unittest.mock import MagicMock

from pytest import raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.create_dataset import create_dataset

from .fixtures import happy_post_client, sad_http_client


def test_it_creates_a_dataset(happy_post_client: Client) -> None:
    dataset = create_dataset(happy_post_client, "test-dataset")
    assert dataset.name == "test-dataset"
    assert dataset.slug == "1337"


def test_it_raises_an_error_on_http_error(sad_http_client: Client) -> None:
    with raises(HTTPError):
        create_dataset(sad_http_client, "test-dataset")
        create_dataset(sad_http_client, "test-dataset")
