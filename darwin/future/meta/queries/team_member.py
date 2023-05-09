from __future__ import annotations

from typing import List, Optional

from darwin.future.core.backend import get_team_members
from darwin.future.core.client import Client
from darwin.future.core.types.query import Modifiers, Query, QueryFilter
from darwin.future.data_objects.darwin_meta import TeamMember, TeamMemberRole


class TeamMemberQuery(Query[TeamMember]):
    def where(self, param: dict[str, str]) -> Query[TeamMember]:
        selected_modifier: Optional[Modifiers] = None
        for modifier in Modifiers:
            if param["value"].startswith(modifier.value):
                selected_modifier = modifier
                break
        if selected_modifier:
            return self + QueryFilter(name=param["name"], param=param["value"], modifier=selected_modifier)
        return self + QueryFilter(name=param["name"], param=param["value"])

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
