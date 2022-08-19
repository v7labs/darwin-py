"""
Holds functions that convert backend errors into a pythonic format the application can understand.
"""

from typing import Any, Dict

from darwin.exceptions import NameTaken, ValidationError


def name_taken(code: int, body: Dict[str, Any]) -> None:
    """
    Validates if a request to the backend errored out with a NameTaken error.

    Parameters
    ----------
    code : int
        The response code.
    body : Dict[str, Any]
        The response body.

    Raises
    ------
    NameTaken
        If both ``code`` and ``body`` indicate that the server request errored due to a name being
        already taken.
    """
    if code != 422:
        return
    if body.get("errors", {}).get("name") == ["has already been taken"]:
        raise NameTaken


def validation_error(code: int, body: Dict[str, Any]) -> None:
    """
    Validates if a request to the backend errored out with a Validation error.

    Parameters
    ----------
    code : int
        The response code.
    body : Dict[str, Any]
        The response body.

    Raises
    ------
    ValidationError
        If both ``code`` and ``body`` indicate that the server request errored because it failed
        validation.
    """
    if code == 422:
        raise ValidationError(body)
