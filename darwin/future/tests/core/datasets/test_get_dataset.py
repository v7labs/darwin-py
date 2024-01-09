import responses
from pytest import raises

from darwin.future.core.client import ClientCore
from darwin.future.core.datasets import get_dataset
from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.exceptions import BadRequest
from darwin.future.tests.core.fixtures import *

from .fixtures import *


def test_it_gets_a_dataset(base_client: ClientCore, basic_dataset: DatasetCore) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + "datasets",
            json=basic_dataset,
            status=200,
        )

        dataset = get_dataset(base_client, "test-dataset")

        assert dataset.name == "test-dataset"
        assert dataset.slug == "1337"


def test_it_raises_an_error_on_http_error(base_client: ClientCore) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + "datasets",
            json={},
            status=400,
        )
        with raises(BadRequest):
            get_dataset(base_client, "test-dataset")
            get_dataset(base_client, "test-dataset")
