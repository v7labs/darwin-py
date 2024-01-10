"""Custom exceptions for the e2e_tests module."""

from typing import Dict, List

from pytest import PytestWarning


class E2EException(PytestWarning):
    """Base class for all exceptions in this module."""

    ...


class E2EEnvironmentVariableNotSet(E2EException):
    """Raised when an environment variable is not set."""

    def __init__(self, name: str, *args: List, **kwargs: Dict) -> None:
        super().__init__(*args, **kwargs)
        self.name = name


class DataAlreadyExists(E2EException):
    """Raised when the teardown process fails and has left legacy data"""

    def __init__(self, name: str, *args: List, **kwargs: Dict) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
