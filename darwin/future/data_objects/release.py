from typing import List

from pydantic import field_validator

from darwin.future.data_objects import validators as darwin_validators
from darwin.future.pydantic_base import DefaultDarwin


class ReleaseCore(DefaultDarwin):
    """
    A class to manage all the information around a release on the darwin platform
    including validation

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
    _name_validator = field_validator("name")(darwin_validators.parse_name)


ReleaseList = List[ReleaseCore]
