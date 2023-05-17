import responses
from pytest import raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.remove_dataset import remove_dataset
from darwin.future.exceptions.base import DarwinException
from darwin.future.tests.core.fixtures import *

from .fixtures import *


def test_it_deletes_a_dataset(base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.DELETE,
            base_client.config.api_endpoint + "datasets",
            json={
                "affected_item_count": 1,
            },
            status=200,
        )

        output = remove_dataset(base_client, "test-dataset")

        assert output["affected_item_count"] == 1


def test_it_throws_http_errors_returned_by_the_client(base_client: Client) -> None:
    with raises(HTTPError):
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.DELETE,
                base_client.config.api_endpoint + "datasets",
                json={
                    "affected_item_count": 1,
                },
                status=400,
            )

            remove_dataset(base_client, "test-dataset")
