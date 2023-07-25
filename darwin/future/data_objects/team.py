from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import validator

from darwin.future.core.client import Client
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
    name: str
    slug: str
    id: int
    datasets: Optional[DatasetList] = None
    members: Optional[List[TeamMember]] = None
    default_role: TeamMemberRole = TeamMemberRole.USER

    # Data Validation
    _slug_validator = validator("slug", allow_reuse=True)(parse_name)

    @staticmethod
    def from_client(client: Client, team_slug: Optional[str] = None) -> Team:
        """Returns the team with the given slug from the client

        Args:
            client (Client): Core client object
            team_slug (Optional[str], optional): team slug str, Defaults to None.

        Returns:
            Team: Team object retrieved from the client with the given slug
        """
        if not team_slug:
            team_slug = client.config.default_team
        return get_team(client, team_slug)


TeamList = List[Team]


def get_team(client: Client, team_slug: Optional[str] = None) -> Team:
    """Returns the team with the given slug from the client

    Args:
        client (Client): Core client object
        team_slug (Optional[str], optional): team slug str, Defaults to None.

    Returns:
        Team: Team object retrieved from the client with the given slug
    """
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/teams/{team_slug}/")
    return Team.parse_obj(response)


def get_team_members(client: Client) -> Tuple[List[TeamMember], List[Exception]]:
    """Returns a list of team members for the given client

    Args:
        client (Client): Core client object

    Returns:
        Tuple[List[TeamMember], List[Exception]]: List of team members and list of errors if any
    """
    response = client.get(f"/memberships")
    members = []
    errors = []
    for item in response:
        try:
            members.append(TeamMember.parse_obj(item))
        except Exception as e:
            errors.append(e)
    return members, errors
