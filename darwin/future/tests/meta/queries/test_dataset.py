import pytest

from darwin.future.core.types import query
from darwin.future.core.types.query import Modifier, QueryFilter
from darwin.future.data_objects.dataset import Dataset
from darwin.future.exceptions.base import DarwinException
from darwin.future.meta.queries.dataset import DatasetQuery

# In progress


# Test instantiation
def test_it_instantiates() -> None:
    DatasetQuery()  # Will not raise an error


def test_it_instantiates_with_filters() -> None:
    DatasetQuery([QueryFilter(name="id", param="1")])  # Will not raise an error


def test_it_instantiates_with_filters_and_modifier() -> None:
    DatasetQuery([QueryFilter(name="id", param="1", modifier=Modifier.GREATER_THAN)])  # Will not raise an error


# Test `by_id` method
@pytest.mark.skip(reason="Not implemented")
def test_by_id_returns_a_dataset_query() -> None:
    ...  # TODO


@pytest.mark.skip(reason="Not implemented")
def test_by_id_raises_an_exception_one_occurs() -> None:
    ...  # TODO


# Test `by_name` method
@pytest.mark.skip(reason="Not implemented")
def test_by_name_returns_a_dataset_query() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_by_name_raises_an_exception_one_occurs() -> None:
    ...


# Test `where` method
def test_where_returns_a_dataset_query() -> None:
    query = DatasetQuery()
    assert isinstance(query.where({"name": "name", "param": "test"}), DatasetQuery)


def test_where_adds_filters_to_the_query() -> None:
    query = DatasetQuery()
    # fmt: off
    query = query.where(
        {
            "name": "name", 
            "param": "test"
        }
    )
    # fmt: on
    assert query.filters == [QueryFilter(name="name", param="test", modifier=None)]


def test_where_adds_multiple_filters() -> None:
    query = DatasetQuery()
    # fmt: off
    query = query.where(
        {
            "name": "name",
            "param": "test"
        }
    )
    # fmt: on
    query = query.where(
        {
            "name": "id",
            "param": "1",
        }
    )
    # fmt: off
    assert query.filters == [
        QueryFilter(
            name="name",
            param="test",
            modifier=None
        ),
        QueryFilter(
            name="id",
            param="1",
            modifier=None
        ),
    ]
    # fmt: on


def test_where_can_be_chained() -> None:
    # fmt: off
    query = (
        DatasetQuery()
        .where(
            {
                "name": "name",
                "param": "test"
            }
        )
        .where(
            {
                "name": "id",
                "param": "1"
            }
        )
        .where(
            {
                "name": "testthing",
                "param": "1337"
            }
        )
    )
    assert query.filters == [
        QueryFilter(name="name", param="test", modifier=None),
        QueryFilter(name="id", param="1", modifier=None),
        QueryFilter(name="testthing", param="1337", modifier=None),
    ]
    # fmt: on


# Test `collect` method
@pytest.mark.skip(reason="Not implemented")
def test_collect_returns_a_list_of_datasets() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_collect_returns_an_empty_list_if_no_datasets_are_found() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_collect_returns_an_empty_list_if_filters_eliminate_all_datasets() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_collect_raises_errors_arising() -> None:
    ...


# Test `_id_filter` method
@pytest.mark.skip(reason="Not implemented")
def test_id_filter_filters_id_on_direct_equality_only() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_id_filter_does_not_filter_on_other_modifiers() -> None:
    ...


# Test `_releases_filter` method
@pytest.mark.skip(reason="Not implemented")
def test_releases_filter_filters_releases_on_direct_equality_only() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_releases_filter_does_not_filter_on_other_modifiers() -> None:
    ...


# Test `_execute_filter` method
@pytest.mark.skip(reason="Not implemented")
def test_uses_internal_filters_for_name_and_id_and_releases() -> None:
    ...


@pytest.mark.skip(reason="Not implemented")
def test_uses_parent_method_for_other_filters() -> None:
    ...
