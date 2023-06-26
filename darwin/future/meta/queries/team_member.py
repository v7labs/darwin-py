from __future__ import annotations

from typing import List

from darwin.future.core.client import Client
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.data_objects.team import TeamMember, get_team_members
from darwin.future.meta.objects.team_member import TeamMembersMeta


class TeamMemberQuery(Query[TeamMembersMeta, TeamMember]):
    """TeamMemberQuery object with methods to manage filters, retrieve data, and execute filters
    Methods:
    where: Adds a filter to the query
    collect: Executes the query and returns the filtered data
    _execute_filter: Executes a filter on a list of objects
    """

    def where(self, param: Param) -> TeamMemberQuery:
        filter = QueryFilter.parse_obj(param)
        query = self + filter

        return TeamMemberQuery(self.client, query.filters)

    def collect(self) -> TeamMembersMeta:
        members, exceptions = get_team_members(self.client)
        if exceptions:
            # TODO: print and or raise exceptions, tbd how we want to handle this
            pass
        if not self.filters:
            self.filters = []
        for filter in self.filters:
            members = self._execute_filter(members, filter)
        return TeamMembersMeta(self.client, members)

    def _execute_filter(self, members: List[TeamMember], filter: QueryFilter) -> List[TeamMember]:
        """Executes filtering on the local list of members, applying special logic for role filtering
        otherwise calls the parent method for general filtering on the values of the members

        Parameters
        ----------
        members : List[TeamMember]
        filter : QueryFilter

        Returns
        -------
        List[TeamMember]: Filtered subset of members
        """
        if filter.name == "role":
            return [m for m in members if filter.filter_attr(m.role.value)]
        else:
            return super()._generic_execute_filter(members, filter)
