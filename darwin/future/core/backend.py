from typing import List, Optional, Tuple

from darwin.future.core.client import CoreClient
from darwin.future.data_objects.team import TeamMemberModel, TeamModel


def get_team(client: CoreClient, team_slug: Optional[str] = None) -> TeamModel:
    """Returns the team with the given slug"""
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/teams/{team_slug}/")
    return TeamModel.parse_obj(response)


def get_team_members(client: CoreClient) -> Tuple[List[TeamMemberModel], List[Exception]]:
    response = client.get("/memberships")
    members = []
    errors = []
    for item in response:
        try:
            members.append(TeamMemberModel.parse_obj(item))
        except Exception as e:
            errors.append(e)
    return (members, errors)
