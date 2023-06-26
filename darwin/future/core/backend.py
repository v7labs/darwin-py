from typing import List, Optional, Tuple

from darwin.future.core.client import Client
from darwin.future.data_objects.team import Team, TeamMember


def get_team(client: Client, team_slug: Optional[str] = None) -> Team:
    """Returns the team with the given slug"""
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/teams/{team_slug}/")
    return Team.parse_obj(response)


def get_team_members(client: Client) -> Tuple[List[TeamMember], List[Exception]]:
    response = client.get("/memberships")
    members = []
    errors = []
    for item in response:
        try:
            members.append(TeamMember.parse_obj(item))
        except Exception as e:
            errors.append(e)
    return (members, errors)
