from typing import Literal, Optional, Union
from uuid import UUID

from darwin.exceptions import DarwinException


def parse_name(name: str) -> str:
    """
    A function to parse and validate a name

    Parameters
    ----------
    name : str
        The name to be parsed and validated

    Returns
    -------
    str
        The parsed and validated name
    """
    assert isinstance(name, str)
    return name.lower().strip()


def validate_uuid(uuid: Union[str, UUID]) -> bool:
    """
    Validates a uuid string

    Parameters
    ----------
    uuid: str
        - the uuid to validate

    Returns
    ----------
    bool
        - True if the uuid is valid, False otherwise
    """
    try:
        if isinstance(uuid, UUID):
            return True

        UUID(uuid)
        return True
    except ValueError:
        return False

    except Exception as e:
        raise DarwinException("Unexpected error validating uuid") from e
