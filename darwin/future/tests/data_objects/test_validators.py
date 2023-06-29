from typing import Union
from unittest.mock import patch

import pytest

from darwin.exceptions import DarwinException
from darwin.future.data_objects.validators import parse_name

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
    parsed = parse_name(input)
    assert parsed == expected


@pytest.mark.parametrize(
    "input",
    [-1, [], 1.0],
)
def test_parse_name_raises_with_incorrect_input(input: Simple) -> None:
    with pytest.raises(AssertionError) as e_info:
        parse_name(input)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "input, expectation",
    [
        ("742d8ce8-15a7-11ee-aa88-7e0b62d29b23", True),
        ("96bfb8de-ecb4-456d-a7a2-243408c77718", True),
        ("c6437ef1-5b86-3a4e-a071-c2d4ad414e6x", False),
        ("c6437ef1-5b86-3a4e-a071-c2d4ad414e6", False),
    ],
)
def test_validate_uuid(input: str, expectation: bool) -> None:
    assert validate_uuid(input) == expectation


def test_validate_uuid_raises_if_unexpected_error_throw() -> None:
    with pytest.raises(DarwinException):
        with patch("darwin.future.data_objects.validators.UUID") as mock_uuid:
            mock_uuid.side_effect = Exception("Unexpected error")
            validate_uuid(1)  # type: ignore[arg-type]
