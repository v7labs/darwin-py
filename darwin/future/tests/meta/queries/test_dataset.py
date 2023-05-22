from unittest.mock import Mock

import pytest

from darwin.future.core.types.query import Modifier, QueryFilter
from darwin.future.data_objects.dataset import Dataset
from darwin.future.exceptions.base import DarwinException
from darwin.future.meta.queries.dataset import DatasetQuery

# In progress


# Test instantiation
def test_it_instantiates():
    DatasetQuery()  # no error


def test_it_instantiates_with_filters():
    DatasetQuery([QueryFilter(name="id", param="1")])  # no error


def test_it_instantiates_with_filters_and_modifier():
    DatasetQuery([QueryFilter(name="id", param="1", modifier=Modifier.GREATER_THAN)])  # no error


def test_it_instantiates_with_filters_and_modifier_and_extra():
    DatasetQuery([QueryFilter(name="id", param="1", modifier=Modifier.GREATER_THAN, extra="extra")])  # no error


# Test `by_id` method
@pytest.mark.skip(reason="Not implemented")
def test_it_returns_a_dataset_query():
    ...  # TODO


@pytest.mark.skip(reason="Not implemented")
def test_it_raises_an_exception_one_occurs():
    ...  # TODO


# Test `by_name` method
@pytest.mark.skip(reason="Not implemented")
def test_it_returns_a_dataset_query():
    ...


@pytest.mark.skip(reason="Not implemented")
def test_it_raises_an_exception_one_occurs():
    ...


# Test `where` method
@pytest.mark.skip(reason="Not implemented")
def test_it_returns_a_dataset_query():
    ...


def test_it_adds_filters_to_the_query():  # TODO: Finish
    query = DatasetQuery()
    query.where({"name": "test"})
    assert query.filters == [QueryFilter(name="name", param="test")]


def test_it_adds_multiple_filters():  # TOOD: Finish
    query = DatasetQuery()
    query.where({"name": "test"})
    query = query.where({"id": "1"})
    assert query.filters == [QueryFilter(name="name", param="test"), QueryFilter(name="id", param="1")]


def test_it_can_be_chained():  # TODO: Finish
    query = DatasetQuery().where({"name": "test"}).where({"id": "1"}).where({"id": "2"})
    assert query.filters == [
        QueryFilter(name="name", param="test"),
        QueryFilter(name="id", param="1"),
        QueryFilter(name="id", param="2"),
    ]


# Test `collect` method
def test_it_returns_a_list_of_datasets():
    ...


def test_it_returns_an_empty_list_if_no_datasets_are_found():
    ...


def test_it_returns_an_empty_list_if_filters_eliminate_all_datasets():
    ...
