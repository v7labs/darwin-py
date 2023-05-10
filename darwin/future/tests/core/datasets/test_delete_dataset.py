from pydantic import ValidationError
from pytest import raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.datasets.remove_dataset import remove_dataset

from .fixtures import happy_get_client, sad_http_client


def test_it_deletes_a_dataset(happy_get_client: Client) -> None:
    happy_get_client.get.return_value = {  # type: ignore
        "affected_item_count": 1,
    }

    output = remove_dataset(happy_get_client, "test-dataset")

    assert output["affected_item_count"] == 1


def test_it_throws_http_errors_returned_by_the_client(sad_http_client: Client) -> None:
    with raises(HTTPError):
        remove_dataset(sad_http_client, "test-dataset")
