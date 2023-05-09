from __future__ import annotations

from typing import List, Optional, Union, overload

from darwin.future.core.backend import get_team_members
from darwin.future.core.client import Client
from darwin.future.core.types.query import Query, QueryFilter
from darwin.future.data_objects.darwin_meta import TeamMember, TeamMemberRole


class TeamMemberQuery(Query[TeamMember]):
    @overload
    def where(self, param: TeamMemberRole) -> Query[TeamMember]:
        ...

    @overload
    def where(self, param: dict[str, str]) -> Query[TeamMember]:
        ...

    def where(self, param: Union[TeamMemberRole, dict[str, str]]) -> Query[TeamMember]:
        if isinstance(param, TeamMemberRole):
            return self + QueryFilter(name="role", param=param.value)
        else:
            return self + QueryFilter(name=param["name"], param=param["value"])

    def collect(self, client: Client) -> List[TeamMember]:
        members, exceptions = get_team_members(client)
        if exceptions:
            # TODO: print and or raise exceptions, tbd how we want to handle this
            pass
        if not self.filters:
            return members
        for filter in self.filters:
            if filter.name == "role":
                members = [m for m in members if m.role == filter.param]
            else:
                members = [m for m in members if getattr(m, filter.name) == filter.param]
        return members
