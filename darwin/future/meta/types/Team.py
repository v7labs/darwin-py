from typing import Optional, Union

from darwin.future.core.client import Client as CoreClient
from darwin.future.data_objects.team import Team as CoreTeam
from darwin.future.data_objects.team import get_team
from darwin.future.meta.queries.team_member import TeamMemberQuery


class Team:
    def __init__(self, client: CoreClient, team: Optional[CoreTeam] = None):
        self.client = client
        if team is None:
            team = get_team(self.client)
        self._team = team

    @property
    def workflows(self) -> None:
        # TODO: implement workflows
        return None

    @property
    def id(self) -> Optional[int]:
        return self._team.id

    @property
    def slug(self) -> str:
        return self._team.slug

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery()
