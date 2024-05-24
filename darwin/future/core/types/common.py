from __future__ import annotations

from typing import Any, Dict, List, Mapping, Protocol, Union

from darwin.future.data_objects import validators as darwin_validators

JSONType = Union[Dict[str, Any], List[Dict[str, Any]]]  # type: ignore
JSONDict = Dict[str, Any]  # type: ignore


class Implements_str(Protocol):
    def __str__(self) -> str: ...


Stringable = Union[str, Implements_str]


class TeamSlug(str):
    """
    Represents a team slug, which is a string identifier for a team.

    Attributes:
    -----------
    min_length : int
        The minimum length of a valid team slug.
    max_length : int
        The maximum length of a valid team slug.

    Methods:
    --------
    __get_validators__() -> generator
        Returns a generator that yields the validator function for this model.
    validate(v: str) -> TeamSlug
        Validates the input string and returns a new TeamSlug object.
    __repr__() -> str
        Returns a string representation of the TeamSlug object.
    """

    min_length = 1
    max_length = 256

    @classmethod
    def validate(cls, v: str) -> "TeamSlug":
        assert (
            len(v) < cls.max_length
        ), f"maximum length for team slug is {cls.max_length}"
        assert (
            len(v) > cls.min_length
        ), f"minimum length for team slug is {cls.min_length}"
        if not isinstance(v, str):
            raise TypeError("string required")
        modified_value = darwin_validators.parse_name(v)
        return cls(modified_value)

    def __repr__(self) -> str:
        return f"TeamSlug({super().__repr__()})"


class QueryString:
    """
    Represents a query string, which is a dictionary of string key-value pairs.

    Attributes:
    -----------
    value : Dict[str, str]
        The dictionary of key-value pairs that make up the query string.

    Methods:
    --------
    dict_check(value: Any) -> Dict[str, str]
        Validates that the input value is a dictionary of string key-value pairs.
        Returns the validated dictionary.
    __init__(value: Dict[str, str]) -> None
        Initializes a new QueryString object with the given dictionary of key-value pairs.
    __str__() -> str
        Returns a string representation of the QueryString object, in the format "?key1=value1&key2=value2".
    """

    value: dict[str, list[str] | str]

    def dict_check(
        self, value: Mapping[str, list[Stringable] | Stringable]
    ) -> dict[str, list[str] | str]:
        mapped: dict[str, list[str] | str] = {}
        for k, v in value.items():
            if isinstance(v, list):
                mapped[k] = [str(x) for x in v]
            else:
                mapped[k] = str(v)
        return mapped

    def __init__(self, value: Mapping[str, list[Stringable] | Stringable]) -> None:
        self.value = self.dict_check(value)

    def __str__(self) -> str:
        output: str = "?" if self.value else ""
        for k, v in self.value.items():
            if isinstance(v, list):
                for x in v:
                    output += f"{k}={x.lower()}&"
            else:
                output += f"{k}={v.lower()}&"
        return output[:-1]  # remove trailing &

    def __add__(self, other: QueryString) -> QueryString:
        return QueryString({**self.value, **other.value})

    def get(self, key: str, default: str = "") -> List[str] | str:
        return self.value.get(key, default)
