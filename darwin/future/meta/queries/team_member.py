from __future__ import annotations

from typing import Any, Dict, List

from darwin.future.core.client import Client
from darwin.future.core.types.query import Query, QueryFilter
from darwin.future.data_objects.team import TeamMember, get_team_members

Param = Dict[str, Any]  # type: ignore


class TeamMemberQuery(Query[TeamMember]):
    """TeamMemberQuery object with methods to manage filters, retrieve data, and execute filters
    Methods:
    where: Adds a filter to the query
    collect: Executes the query and returns the filtered data
    _execute_filter: Executes a filter on a list of objects
    """

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
            if filter.name == "role":
                members = filter.apply_to_objects(members, "role.value")
            else:
                members = filter.apply_to_objects(members)
        return members
