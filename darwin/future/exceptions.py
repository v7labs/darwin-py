from __future__ import annotations

from typing import Optional, Sequence


from darwin.future.data_objects.typing import KeyValuePairDict, UnknownType


class DarwinException(Exception):
    """
    Generic Darwin exception.

    Used to differentiate from errors that originate in our code, and those that
    originate in third-party libraries.

    Extends `Exception` and adds a `parent_exception` field to store the original
    exception.

    Also has a `combined_exceptions` field to store a list of exceptions that were
    combined into
    """

    parent_exception: Optional[Exception] = None
    combined_exceptions: Optional[Sequence[Exception]] = None

    def __init__(self, *args: UnknownType, **kwargs: KeyValuePairDict) -> None:
        super().__init__(*args, **kwargs)

    @classmethod
    def from_exception(cls, exc: Exception) -> DarwinException:
        """
        Creates a new exception from an existing exception.

        Parameters
        ----------
        exc: Exception
            The existing exception.

        Returns
        -------
        DarwinException
            The new exception.
        """
        instance = cls(str(exc))
        instance.parent_exception = exc

        return instance

    @classmethod
    def from_multiple_exceptions(
        cls, exceptions: Sequence[Exception]
    ) -> DarwinException:
        """
        Creates a new exception from a list of exceptions.

        Parameters
        ----------
        exceptions: List[Exception]
            The list of exceptions.

        Returns
        -------
        DarwinException
            The new exception.
        """
        instance = cls(
            f"Multiple errors occurred while exporting: {', '.join([str(e) for e in exceptions])}",
        )
        instance.combined_exceptions = exceptions

        return instance

    def __str__(self) -> str:
        output_string = f"{self.__class__.__name__}: {super().__str__()}\n"
        if self.parent_exception:
            output_string += f"Parent exception: {self.parent_exception}\n"

        if self.combined_exceptions:
            output_string += f"Combined exceptions: {self.combined_exceptions}\n"

        return output_string

    def __repr__(self) -> str:
        return super().__repr__()


class ValidationError(DarwinException):
    pass


class AssertionError(DarwinException):
    pass


class NotFound(DarwinException):
    pass


class UnprocessibleEntity(DarwinException):
    pass


class Unauthorized(DarwinException):
    pass


class UnrecognizableFileEncoding(DarwinException):
    pass


class BadRequest(DarwinException):
    pass


class MissingSlug(DarwinException):
    pass


class MissingDataset(DarwinException):
    pass


class ResultsNotFound(DarwinException):
    pass


class MoreThanOneResultFound(DarwinException):
    pass


class InvalidQueryModifier(DarwinException):
    pass


class InvalidQueryFilter(DarwinException):
    pass


class DatasetNotFound(DarwinException):
    """Raised when the dataset endpoint returns a malformed response."""

    ...


class MaxRetriesError(DarwinException):
    """Raised when a certain API call is re-tried for {x} number of times."""

    ...
