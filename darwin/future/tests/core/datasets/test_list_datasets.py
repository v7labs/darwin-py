from typing import List

import responses
from requests.exceptions import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.types import TeamSlug
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.dataset import Dataset
from darwin.future.tests.core.fixtures import *

from .fixtures import *


def test_it_lists_datasets(base_client: Client, basic_list_of_datasets: List[Dataset]) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + "datasets",
            json=basic_list_of_datasets,
            status=200,
        )

        datasets, errors = list_datasets(base_client)

        assert len(errors) == 0

        assert len(datasets) == 3
        assert datasets[0].name == "test-dataset"
        assert datasets[0].slug == "1337"


def test_it_returns_an_error_if_the_client_returns_an_http_error(base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + "datasets",
            json={},
            status=400,
        )

        response, errors = list_datasets(base_client)

        assert len(errors) == 1
        assert isinstance(error := errors[0], HTTPError)
        assert error.response.status_code == 400
        assert not response
