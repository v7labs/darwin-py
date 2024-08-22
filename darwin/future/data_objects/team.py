from __future__ import annotations

from typing import List, Optional

from pydantic import field_validator

from darwin.future.core.client import ClientCore
from darwin.future.core.team.get_raw import get_team_raw
from darwin.future.data_objects.dataset import DatasetList
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.data_objects.validators import parse_name
from darwin.future.pydantic_base import DefaultDarwin


class TeamMemberCore(DefaultDarwin):
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


TeamMemberList = List[TeamMemberCore]


class TeamCore(DefaultDarwin):
    """
    A class to manage all the information around a Team on the darwin platform
    including validation

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

    name: str
    slug: str
    id: int
    datasets: Optional[DatasetList] = None
    members: Optional[List[TeamMemberCore]] = None
    default_role: TeamMemberRole = TeamMemberRole.USER

    # Data Validation
    _slug_validator = field_validator("slug")(parse_name)

    @staticmethod
    def from_client(client: ClientCore, team_slug: Optional[str] = None) -> TeamCore:
        """Returns the team with the given slug from the client

        Args:
            client (Client): Core client object
            team_slug (Optional[str], optional): team slug str, Defaults to None.

        Returns:
            Team: Team object retrieved from the client with the given slug
        """
        if not team_slug:
            team_slug = client.config.default_team
        url = client.config.api_endpoint + f"teams/{team_slug}"
        return TeamCore.model_validate(get_team_raw(client.session, url))
