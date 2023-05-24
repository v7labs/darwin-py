import responses
from pydantic import ValidationError
from pytest import raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.data_objects.dataset import Dataset
from darwin.future.tests.core.fixtures import *

from .fixtures import *


def test_it_gets_a_dataset(base_client: Client, basic_dataset: Dataset) -> None:
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


def test_it_raises_an_error_on_http_error(base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + "datasets",
            json={},
            status=400,
        )
        with raises(HTTPError):
            get_dataset(base_client, "test-dataset")
            get_dataset(base_client, "test-dataset")


def test_it_raises_an_error_on_pydantic_error(sad_client_pydantic: Client) -> None:
    with raises(ValidationError):
        get_dataset(sad_client_pydantic, "test-dataset")
