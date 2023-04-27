from typing import Optional

from darwin.future.core.client import Client
from darwin.future.data_objects.darwin_meta import Team


def get_team(client: Client, team_slug: Optional[str] = None) -> Team:
    """Returns the team with the given slug"""
    if not team_slug:
        team_slug = client.config.default_team
    response = client.get(f"/teams/{team_slug}/")
    return Team.parse_obj(response)
