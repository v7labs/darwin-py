from pytest import raises
from requests import HTTPError
from darwin.future.exceptions.base import DarwinException
import responses

from darwin.future.core.client import Client
from darwin.future.core.datasets.remove_dataset import remove_dataset

from .fixtures import *
from darwin.future.tests.core.fixtures import *


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
    for code in [400, 401, 403, 404, 500]:
        with raises((HTTPError, DarwinException)):
            with responses.RequestsMock() as rsps:
                rsps.add(
                    rsps.DELETE,
                    base_client.config.api_endpoint + "datasets",
                    json={
                        "affected_item_count": 1,
                    },
                    status=code,
                )

                remove_dataset(base_client, "test-dataset")
