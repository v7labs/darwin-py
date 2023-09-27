from typing import List, Optional

from darwin.future.core.client import ClientCore
from darwin.future.core.team.get_team import get_team
from darwin.future.data_objects.team import TeamCore
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.dataset import DatasetQuery
from darwin.future.meta.queries.team_member import TeamMemberQuery
from darwin.future.meta.queries.workflow import WorkflowQuery


class Team(MetaBase[TeamCore]):
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

    def __init__(self, client: ClientCore, team: Optional[TeamCore] = None) -> None:
        team = team or get_team(client)
        super().__init__(client, team)

    @property
    def name(self) -> str:
        return self._element.name

    @property
    def id(self) -> int:
        assert self._element.id is not None
        return self._element.id

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client, meta_params={"team_slug": self.slug})

    @property
    def slug(self) -> str:
        return self._element.slug

    @property
    def datasets(self) -> DatasetQuery:
        return DatasetQuery(self.client, meta_params={"team_slug": self.slug})

    @property
    def workflows(self) -> WorkflowQuery:
        return WorkflowQuery(self.client, meta_params={"team_slug": self.slug})

    def __str__(self) -> str:
        return f"TeamMeta(name='{self.name}', slug='{self.slug}', id='{self.id}' - {len(self._element.members if self._element.members else [])} members)"
