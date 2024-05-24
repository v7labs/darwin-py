import responses
from pytest import raises

from darwin.future.core.client import ClientCore
from darwin.future.core.datasets import remove_dataset
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *

from .fixtures import *


def test_it_deletes_a_dataset(base_client: ClientCore) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.PUT,
            base_client.config.api_endpoint + "datasets/1337/archive",
            json={
                "id": 1337,
            },
            status=200,
        )

        output = remove_dataset(base_client, 1337)

        assert output == 1337


def test_it_throws_http_errors_returned_by_the_client(base_client: ClientCore) -> None:
    with raises(BadRequest):
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.PUT,
                base_client.config.api_endpoint + "datasets/test-dataset/archive",
                json={
                    "affected_item_count": 1,
                },
                status=400,
            )

            remove_dataset(base_client, "test-dataset")  # type: ignore
