import unittest
from typing import Union

import pytest

from darwin.future.data_objects import validators as validators

Simple = Union[list, tuple, dict, str, int, float]


@pytest.mark.parametrize(
    "input,expected",
    [
        ("UPPERCASE", "uppercase"),
        ("lowercase", "lowercase"),
        (" whitespace ", "whitespace"),
        ("middle white space", "middle white space"),
        (" Inte grated Test ", "inte grated test"),
    ],
)
def test_parse_name_parses_correctly(input: str, expected: str) -> None:
    parsed = validators.parse_name(input)
    assert parsed == expected


@pytest.mark.parametrize(
    "input",
    [-1, [], 1.0],
)
def test_parse_name_raises_with_incorrect_input(input: Simple) -> None:
    with pytest.raises(AssertionError) as e_info:
        validators.parse_name(input)  # type: ignore[arg-type]
