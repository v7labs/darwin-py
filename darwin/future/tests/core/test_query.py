import unittest
from typing import List

import pytest

from darwin.future.core.types import query as Query
from darwin.future.data_objects.darwin_meta import Team


@pytest.fixture
def basic_filters() -> List[Query.QueryFilter]:
    return [
        Query.QueryFilter(name="test1", param="test1"),
        Query.QueryFilter(name="test2", param="test2"),
        Query.QueryFilter(name="test3", param="test3"),
    ]


@pytest.fixture
def test_team() -> Team:
    return Team(slug="test-team", id=0)


def test_query_instantiated(basic_filters: List[Query.QueryFilter], test_team: Team) -> None:
    q = Query.Query(test_team, basic_filters)
    assert q.filters == basic_filters


def test_query_filter_functionality(basic_filters: List[Query.QueryFilter], test_team: Team) -> None:
    q = Query.Query(test_team)
    for f in basic_filters:
        q = q.filter(f)
    assert q.filters == basic_filters
    dropped_filter = basic_filters.pop(0)
    q = q - dropped_filter
    assert q.filters == basic_filters
    basic_filters.append(dropped_filter)
    q = q + dropped_filter
    assert q.filters == basic_filters

    # Test filter drops from middle
    dropped_filter = basic_filters.pop(1)
    q = q - dropped_filter
    assert q.filters == basic_filters
    basic_filters.append(dropped_filter)
    q = q + dropped_filter
    assert q.filters == basic_filters


def test_query_iterable(basic_filters: List[Query.QueryFilter], test_team: Team) -> None:
    q = Query.Query(test_team, basic_filters)
    for i, f in enumerate(q):
        assert f == basic_filters[i]
    assert q.filters is not None
    assert len(q) == len(basic_filters)
