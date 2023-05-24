from typing import List
from unittest.mock import MagicMock, patch

import pytest
import responses
from pydantic import ValidationError
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

        datasets = list_datasets(base_client)

        assert len(datasets) == 3
        assert datasets[0].name == "test-dataset"
        assert datasets[0].slug == "1337"


def test_it_raises_an_error_if_the_client_returns_an_http_error(base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_client.config.api_endpoint + "datasets",
            json={},
            status=400,
        )
        with pytest.raises(HTTPError):
            list_datasets(base_client)


def test_it_raises_an_error_if_the_client_returns_a_pydantic_error(sad_client_pydantic: Client) -> None:
    with pytest.raises(ValidationError):
        list_datasets(sad_client_pydantic)
