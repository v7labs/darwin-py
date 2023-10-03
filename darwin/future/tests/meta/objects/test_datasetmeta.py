import string
from typing import Generator
from unittest.mock import Mock, patch

from pytest import fixture, mark, raises
from responses import RequestsMock

from darwin.future.core.client import DarwinConfig
from darwin.future.meta.client import Client
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.tests.core.fixtures import *


@fixture
def _delete_by_slug_mock() -> Generator:
    with patch.object(Dataset, "_delete_by_slug") as mock:
        yield mock


@fixture
def _delete_by_id_mock() -> Generator:
    with patch.object(Dataset, "_delete_by_id") as mock:
        yield mock


# `datasets` tests
# TODO datasets tests

# `get_dataset_by_id` tests
# TODO get_dataset_by_id tests


# `create_dataset` tests
def test_create_dataset_returns_exceptions_thrown(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(rsps.POST, base_url, status=500)

        exceptions, dataset_created = Dataset.create_dataset(valid_client, valid_slug)

        assert exceptions is not None
        assert "500 Server Error" in str(exceptions[0])
        assert dataset_created is None


def test_create_dataset_returns_dataset_created_if_dataset_created(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            base_url,
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=201,
        )

        exceptions, dataset_created = Dataset.create_dataset(valid_client, valid_slug)

        assert exceptions is None
        assert dataset_created is not None
        assert dataset_created.id == 1
        assert dataset_created.name == "test dataset"
        assert dataset_created.slug == "test_dataset"


# `update_dataset` tests
# TODO update_dataset tests


# `delete_dataset` tests
def test_delete_dataset_returns_exceptions_thrown(
    base_config: DarwinConfig, _delete_by_id_mock: Mock, _delete_by_slug_mock: Mock
) -> None:
    _delete_by_slug_mock.side_effect = Exception("test exception")

    valid_client = Client(base_config)

    exceptions, dataset_deleted = Dataset.delete_dataset(valid_client, "test_dataset")

    assert exceptions is not None
    assert str(exceptions[0]) == "test exception"
    assert dataset_deleted == -1

    assert _delete_by_slug_mock.call_count == 1
    assert _delete_by_id_mock.call_count == 0


def test_delete_dataset_calls_delete_by_slug_as_appropriate(
    base_config: DarwinConfig, _delete_by_id_mock: Mock, _delete_by_slug_mock: Mock
) -> None:
    valid_client = Client(base_config)

    exceptions, _ = Dataset.delete_dataset(valid_client, "test_dataset")

    assert exceptions is None
    assert _delete_by_slug_mock.call_count == 1
    assert _delete_by_id_mock.call_count == 0


def test_delete_dataset_calls_delete_by_id_as_appropriate(
    base_config: DarwinConfig, _delete_by_id_mock: Mock, _delete_by_slug_mock: Mock
) -> None:
    valid_client = Client(base_config)

    exceptions, _ = Dataset.delete_dataset(valid_client, 1)

    assert exceptions is None
    assert _delete_by_slug_mock.call_count == 0
    assert _delete_by_id_mock.call_count == 1


# Test `_delete_by_slug`
def test_delete_by_slug_raises_exception_if_not_passed_str_and_client(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"
    invalid_client = "client"
    invalid_slug = 1

    with raises(AssertionError):
        Dataset._delete_by_slug(valid_client, invalid_slug)  # type: ignore

    with raises(AssertionError):
        Dataset._delete_by_slug(invalid_client, valid_slug)  # type: ignore


def test_delete_by_slug__returns_dataset_deleted_if_dataset_found(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(
            rsps.GET,
            base_url + "?id=test_dataset",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        rsps.add(
            rsps.PUT,
            base_url + "/1/archive",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        dataset_deleted = Dataset._delete_by_slug(valid_client, valid_slug)

        assert dataset_deleted == 1


# Test `_delete_by_id`
def test_delete_by_id_raises_exception_if_not_passed_int_and_client(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_id = 1
    invalid_client = "client"
    invalid_id = "1"

    with raises(AssertionError):
        Dataset._delete_by_id(valid_client, invalid_id)  # type: ignore

    with raises(AssertionError):
        Dataset._delete_by_id(invalid_client, valid_id)  # type: ignore


def test_delete_by_id_returns_dataset_deleted_if_dataset_found(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_id = 1

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(
            rsps.PUT,
            base_url + "/1/archive",
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=200,
        )
        dataset_deleted = Dataset._delete_by_id(valid_client, valid_id)

        assert dataset_deleted == 1


@mark.parametrize(
    "invalid_slug",
    ["", " ", "test dataset", *[f"dataset_{c}" for c in string.punctuation if c not in ["-", "_", "."]]],
)
def test_validate_slugh_raises_exception_if_passed_invalid_inputs(invalid_slug: str) -> None:
    with raises(AssertionError):
        Dataset._validate_slug(invalid_slug)


def test_validate_slug_returns_none_if_passed_valid_slug() -> None:
    valid_slug = "test-dataset"

    assert Dataset._validate_slug(valid_slug) is None
