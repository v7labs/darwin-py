from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, PositiveInt, validator

from darwin.future.data_objects import validators as darwin_validators


class TeamMemberRole(Enum):
    TEAM_OWNER = "owner"
    TEAM_ADMIN = "admin"
    USER = "member"
    WORKFORCE_MANAGER = "workforce_manager"
    WORKER = "annotator"


class DefaultDarwin(BaseModel):
    """Default Darwin-Py pydantic settings for meta information.
    Default settings include:
        - auto validating variables on setting/assignment
        - underscore attributes are private
        - objects are passed by reference to prevent unnecesary data copying
    """

    class Config:
        validate_assignment = True
        underscore_attrs_are_private = True
        copy_on_model_validation = "none"


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

    # Data Validation
    _name_validator = validator("name", allow_reuse=True)(darwin_validators.parse_name)


class Dataset(DefaultDarwin):
    """A class to manage all the information around a dataset on the darwin platform, including validation

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
    releases: Optional[List[Release]] = None

    # Data Validation
    _name_validator = validator("name", allow_reuse=True)(darwin_validators.parse_name)


class TeamMember(DefaultDarwin):
    """A class to manage all the information around a team member on the darwin platform
    Attributes
    ----------
    name: str
    """

    email: str
    first_name: str
    last_name: str
    role: TeamMemberRole
    team_id: int
    id: int
    user_id: int


class Team(DefaultDarwin):
    """A class to manage all the information around a Team on the darwin platform, including validation

    Attributes
    ----------
    slug : str
    datasets: Optional[List[Dataset]] = None
        - a list of datasets linked to the team
    members: Optional[List[Release]] = None
        - a list of members linked to a team
    Methods
    ----------
    _slug_validator: validates and auto formats the slug variable
    """

    slug: str
    id: int
    datasets: Optional[List[Dataset]] = None
    members: Optional[List[TeamMember]] = None
    default_role: TeamMemberRole = TeamMemberRole.USER

    # Data Validation
    _slug_validator = validator("slug", allow_reuse=True)(darwin_validators.parse_name)
