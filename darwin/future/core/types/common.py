from typing import Dict

from pydantic import ConstrainedStr

from darwin.future.data_objects import validators as darwin_validators


class TeamSlug(ConstrainedStr):
    """Team slug type"""

    min_length = 1
    max_length = 100

    validator = darwin_validators.parse_name


class QueryString:
    """Query string type"""

    def __init__(self, value: Dict[str, str]) -> None:
        assert isinstance(value, dict)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in value.items())

        self.value = value

    def __str__(self) -> str:
        return "&".join(f"{k}={v}" for k, v in self.value.items())
