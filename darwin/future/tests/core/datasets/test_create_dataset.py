from typing import Union

import responses
from pytest import raises
from requests import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.create_dataset import create_dataset
from darwin.future.data_objects.dataset import Dataset
from darwin.future.exceptions.base import DarwinException
from darwin.future.tests.core.fixtures import *  # noqa: F401, F403

from .fixtures import *  # noqa: F401, F403


def test_it_creates_a_dataset(basic_dataset: Dataset, base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            base_client.config.api_endpoint + "datasets",
            json=basic_dataset,
            status=200,
        )

        dataset = create_dataset(base_client, "test-dataset")
        assert dataset.name == "test-dataset"
        assert dataset.slug == "1337"


def test_it_raises_an_error_on_http_error(basic_dataset: Dataset, base_client: Client) -> None:
    with raises(HTTPError):
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.POST,
                base_client.config.api_endpoint + "datasets",
                json=basic_dataset,
                status=400,
            )

            create_dataset(base_client, "test-dataset")

