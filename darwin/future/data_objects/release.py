from typing import List

from pydantic import validator

from darwin.future.data_objects import validators as darwin_validators
from darwin.future.pydantic_base import DefaultDarwin


class Release(DefaultDarwin):
    """A class to manage all the information around a release on the darwin platform, including validation
    Attributes
    ----------
    name : str

    Methods
    ----------
    _name_validator: validates and auto formats the name variable
    """

    name: str

    def __str__(self) -> str:
        return self.name

    # Data Validation
    _name_validator = validator("name", allow_reuse=True)(darwin_validators.parse_name)


ReleaseList = List[Release]
