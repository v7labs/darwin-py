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

    client: Client

    def __init__(self, client: Client, teams: Optional[List[Team]] = None) -> None:
        # TODO: Initialise from chaining within Client
        self.client = client
        if not teams:
            teams = [get_team(self.client)]
        super().__init__(teams)

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client)
