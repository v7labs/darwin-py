from typing import List, Optional, Tuple

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.team import TeamCore, TeamMemberCore


def get_team(client: ClientCore, team_slug: Optional[str] = None) -> TeamCore:
    """Returns the team with the given slug"""
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/teams/{team_slug}/")
    return TeamCore.parse_obj(response)


def get_team_members(client: ClientCore) -> Tuple[List[TeamMemberCore], List[Exception]]:
    response = client.get("/memberships")
    members = []
    errors = []
    for item in response:
        try:
            members.append(TeamMemberCore.parse_obj(item))
        except Exception as e:
            errors.append(e)
    return (members, errors)
