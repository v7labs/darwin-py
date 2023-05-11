from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from requests.exceptions import HTTPError

from darwin.future.core.client import Client
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.types import TeamSlug
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.dataset import Dataset

from .fixtures import happy_get_client, sad_client_pydantic, sad_http_client


def test_it_lists_datasets(happy_get_client: Client) -> None:
    datasets = list_datasets(happy_get_client)

    assert len(datasets) == 1

    assert datasets[0].name == "test-dataset"
    assert datasets[0].slug == "1337"


def test_it_raises_an_error_if_the_client_returns_an_http_error(sad_http_client: Client) -> None:
    with pytest.raises(HTTPError):
        list_datasets(sad_http_client)


def test_it_raises_an_error_if_the_client_returns_a_pydantic_error(sad_client_pydantic: Client) -> None:
    with pytest.raises(ValidationError):
        list_datasets(sad_client_pydantic)
