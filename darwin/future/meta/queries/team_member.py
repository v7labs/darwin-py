from __future__ import annotations

from typing import List

from darwin.future.core.team.get_team import get_team_members
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.meta.objects.team_member import TeamMember


class TeamMemberQuery(Query[TeamMember]):
    """TeamMemberQuery object with methods to manage filters, retrieve data, and execute filters
    Methods:
    collect: Executes the query and returns the filtered data
    _execute_filter: Executes a filter on a list of objects
    """

    def _collect(self) -> List[TeamMember]:
        members, exceptions = get_team_members(self.client)
        members_meta = [TeamMember(self.client, member) for member in members]
        if exceptions:
            # TODO: print and or raise exceptions, tbd how we want to handle this
            pass
        if not self.filters:
            self.filters = []
        for filter in self.filters:
            members_meta = self._execute_filter(members_meta, filter)

        return members_meta

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
            return [m for m in members if m._element is not None and filter.filter_attr(m._element.role.value)]
        else:
            return super()._generic_execute_filter(members, filter)
