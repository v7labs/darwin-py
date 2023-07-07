from typing import List, Optional

from darwin.future.core.client import Client
from darwin.future.data_objects.team import Team, get_team
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.team_member import TeamMemberQuery


class TeamMeta(MetaBase[Team]):
    """Team Meta object. Facilitates the creation of Query objects, lazy loading of sub fields like members
    unlike other MetaBase objects, does not extend the __next__ function because it is not iterable. This is because
    Team is linked to api key and only one team can be returned, but stores a list of teams for consistency. This
    does mean however that to access the underlying team object, you must access the first element of the list
    team = client.team[0]

    Args:
        MetaBase (Team): Generic MetaBase object expanded by Team core object return type

    Returns:
        _type_: TeamMeta
    """

    def __init__(self, client: Client, team: Optional[Team] = None) -> None:
        team = team or get_team(client)
        super().__init__(client, team)

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client)

    # @property
    # def workflows(self) -> WorkflowQuery:
    #     return WorkflowQuery(self.client)
