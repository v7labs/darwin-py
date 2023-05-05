from typing import List, Optional

from darwin.future.core.backend import get_team_members
from darwin.future.core.client import Client
from darwin.future.core.types.query import ClientSideQuery, Query, QueryFilter
from darwin.future.data_objects.darwin_meta import TeamMember, TeamMemberRole


class TeamMemberQuery(Query[TeamMember]):
    def collect(self, client: Client) -> List[TeamMember]:
        members, exceptions = get_team_members(client)
        return members
