from typing import List, Optional

from pydantic import PositiveInt, validator

from darwin.future.data_objects.release import ReleaseList
from darwin.future.data_objects.validators import parse_name
from darwin.future.pydantic_base import DefaultDarwin


class Dataset(DefaultDarwin):
    """
    A class to manage all the information around a dataset on the darwin platform,
    including validation

    Attributes
    ----------
    name : str
    slug : str
    id: Optional[int] = None
    releases: Optional[List[Release]] = None
        - a list of export releases linked to a dataset
    Methods
    ----------
    _name_validator: validates and auto formats the name variable
    """

    name: str
    slug: str
    id: Optional[PositiveInt] = None
    releases: Optional[ReleaseList] = None

    # Data Validation
    _name_validator = validator("name", allow_reuse=True)(parse_name)


DatasetList = List[Dataset]
