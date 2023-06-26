from typing import List, Optional

from darwin.future.core.client import Client
from darwin.future.data_objects.team import Team
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.team_member import TeamMemberQuery


class TeamMeta(MetaBase[Team]):
    client: Client

    def __init__(self, client: Client, teams: Optional[List[Team]]=None) -> None:
        # TODO: Initialise from chaining within MetaClient
        self.client = client
        super().__init__(teams)
    

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client)