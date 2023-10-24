from typing import Any, Dict, List, Union

from darwin.future.data_objects import validators as darwin_validators
from darwin.future.data_objects.typing import UnknownType

JSONType = Union[Dict[str, Any], List[Dict[str, Any]]]  # type: ignore


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
    def __get_validators__(cls):  # type: ignore
        yield cls.validate

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

    value: Dict[str, str]

    def dict_check(self, value: UnknownType) -> Dict[str, str]:
        assert isinstance(value, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())
        return value

    def __init__(self, value: Dict[str, str]) -> None:
        self.value = self.dict_check(value)

    def __str__(self) -> str:
        return "?" + "&".join(f"{k}={v}" for k, v in self.value.items())
