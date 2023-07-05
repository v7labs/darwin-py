from typing import List

from darwin.exceptions import DarwinException
from darwin.future.core.client import Client
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.core.workflows.list_workflows import list_workflows
from darwin.future.data_objects.workflow import Workflow
from darwin.future.helpers.exception_handler import handle_exception


class WorkflowQuery(Query[Workflow]):
    """
    WorkflowQuery object with methods to manage filters, retrieve data, and execute
    filters

    Methods
    -------

    where: Adds a filter to the query
    collect: Executes the query and returns the filtered data
    """

    def where(self, param: Param) -> "WorkflowQuery":
        filter = QueryFilter.parse_obj(param)
        query = self + filter

        return WorkflowQuery(query.filters)

    def collect(self, client: Client) -> List[Workflow]:
        workflows, exceptions = list_workflows(client)
        if exceptions:
            handle_exception(exceptions)
            raise DarwinException from exceptions[0]

        if not self.filters:
            return workflows

        for filter in self.filters:
            workflows = self._execute_filters(workflows, filter)

        return workflows

    def _execute_filters(self, workflows: List[Workflow], filter: QueryFilter) -> List[Workflow]:
        # TODO implement filtering on workflows

        return self._generic_execute_filter(workflows, filter)
