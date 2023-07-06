import unittest
from typing import Any, List, Optional, Type

import pytest

from darwin.future.core.client import Client
from darwin.future.core.types import query as Query
from darwin.future.data_objects.team import Team
from darwin.future.tests.core.fixtures import *


@pytest.fixture
def non_abc_query() -> Type[Query.Query]:
    """Query is an abstract base class, this fixture removes the abstract methods
    so that it can be instantiated for testing the default methods
    """
    fixed = Query.Query
    fixed.__abstractmethods__ = set()  # type: ignore
    return fixed


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


def test_query_instantiated(base_client: Client, basic_filters: List[Query.QueryFilter], non_abc_query: Type[Query.Query]) -> None:
    q = non_abc_query(base_client, basic_filters)
    assert q.filters == basic_filters


def test_query_filter_functionality(base_client: Client, basic_filters: List[Query.QueryFilter], non_abc_query: Type[Query.Query]) -> None:
    q = non_abc_query(base_client)
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



@pytest.mark.parametrize(
    "mod,param,check,expected",
    [
        (None, "test", "test", True),  # test str equalities
        ("!=", "test", "test", False),
        ("contains", "test", "test", True),
        (None, "test", "test1", False),  # test str inequalites
        ("!=", "test", "test1", True),
        ("contains", "test1", "test", False),
        (None, 1, 1, True),  # test int equalities
        ("!=", 1, 1, False),
        (">", 1, 2, True),
        (">=", 1, 1, True),
        ("<", 1, 1, False),
        ("<=", 1, 1, True),
        (">", 1, 1, False),  # test int inequalites
        ("<", 1, 2, False),
        (">=", 1, 0, False),
        ("<=", 1, 2, False),
        (None, 1, 2, False),
        ("!=", 1, 2, True),
    ],
)
def test_query_filter_filters(mod: Optional[str], param: Any, check: Any, expected: bool) -> None:  # type: ignore
    # test str
    if mod:
        modifier = Query.Modifier(mod)
    else:
        modifier = None
    QF = Query.QueryFilter(name="test", param=param, modifier=modifier)
    assert QF.filter_attr(check) == expected
