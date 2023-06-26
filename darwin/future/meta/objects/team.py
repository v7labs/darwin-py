from typing import List, Optional

from darwin.future.data_objects.team import Team
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.client import MetaClient
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.team_member import TeamMemberQuery


class TeamMeta(MetaBase[Team]):
    client: MetaClient

    def __init__(self, client: MetaClient, team: Optional[Team]=None) -> None:
        # TODO: Initialise from chaining within MetaClient
        self.client = client
        self.team = team
    

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client)