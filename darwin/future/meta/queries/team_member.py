from __future__ import annotations

from typing import Any, Dict, List

from darwin.future.core.backend import get_team_members
from darwin.future.core.client import Client
from darwin.future.core.types.query import Modifiers, Query, QueryFilter
from darwin.future.data_objects.team import TeamMember
from darwin.future.data_objects.team_member_role import TeamMemberRole

Param = Dict[str, Any]  # type: ignore


class TeamMemberQuery(Query[TeamMember]):
    def where(self, param: Param) -> TeamMemberQuery:
        filter = QueryFilter.parse_obj(param)
        query = self + filter
        return TeamMemberQuery(query.filters)

    def collect(self, client: Client) -> List[TeamMember]:
        members, exceptions = get_team_members(client)
        if exceptions:
            # TODO: print and or raise exceptions, tbd how we want to handle this
            pass
        if not self.filters:
            return members
        for filter in self.filters:
            members = self._execute_filter(members, filter)
        return members

    def _execute_filter(self, members: List[TeamMember], filter: QueryFilter) -> List[TeamMember]:
        if filter.name == "role":
            return [m for m in members if filter.filter_attr(m.role.value)]
        else:
            return super()._generic_execute_filter(members, filter)
