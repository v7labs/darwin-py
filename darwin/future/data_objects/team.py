from typing import List, Optional

from pydantic import validator

from darwin.future.data_objects.dataset import DatasetList
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.data_objects.validators import parse_name
from darwin.future.pydantic_base import DefaultDarwin


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


TeamMemberList = List[TeamMember]


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
    datasets: Optional[DatasetList] = None
    members: Optional[List[TeamMember]] = None
    default_role: TeamMemberRole = TeamMemberRole.USER

    # Data Validation
    _slug_validator = validator("slug", allow_reuse=True)(parse_name)


TeamList = List[Team]
