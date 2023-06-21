from darwin.future.exceptions.base import DarwinException


class DatasetException(DarwinException):
    """Base class for all dataset exceptions."""

    ...


class DatasetNotFound(DatasetException):
    """Raised when the dataset endpoint returns a malformed response."""

    ...
