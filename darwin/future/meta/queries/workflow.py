from datetime import datetime, timezone
from typing import List
from uuid import UUID

from darwin.exceptions import DarwinException
from darwin.future.core.client import Client
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.core.workflows.list_workflows import list_workflows
from darwin.future.data_objects.workflow import WFStage, Workflow
from darwin.future.helpers.exception_handler import handle_exception
from darwin.future.meta.objects.workflow import WorkflowMeta


class WorkflowQuery(Query[WorkflowMeta, Workflow]):
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

        return WorkflowQuery(self.client, query.filters)

    def collect(self) -> List[Workflow]:
        workflows, exceptions = list_workflows(self.client)
        if exceptions:
            handle_exception(exceptions)
            raise DarwinException from exceptions[0]

        if not self.filters:
            return workflows

        for filter in self.filters:
            workflows = self._execute_filters(workflows, filter)

        return workflows

    def _execute_filters(self, workflows: List[Workflow], filter: QueryFilter) -> List[Workflow]:
        if filter.name == "id":
            id_to_find = UUID(filter.param)
            return [w for w in workflows if w.id == id_to_find]

        if filter.name == "inserted_at_start":
            start_date = datetime.fromisoformat(filter.param)
            return [w for w in workflows if self._date_compare(w.inserted_at, start_date)]

        if filter.name == "inserted_at_end":
            end_date = datetime.fromisoformat(filter.param)
            return [w for w in workflows if self._date_compare(end_date, w.inserted_at)]

        if filter.name == "updated_at_start":
            start_date = datetime.fromisoformat(filter.param)
            return [w for w in workflows if self._date_compare(w.updated_at, start_date)]

        if filter.name == "updated_at_end":
            end_date = datetime.fromisoformat(filter.param)
            return [w for w in workflows if self._date_compare(end_date, w.updated_at)]

        if filter.name == "dataset_id":
            datasets_to_find_id: List[int] = [int(s) for s in filter.param.split(",")]
            return [w for w in workflows if int(w.dataset) in datasets_to_find_id]

        if filter.name == "dataset_name":
            datasets_to_find_name: List[str] = [str(s) for s in filter.param.split(",")]
            return [w for w in workflows if str(w.dataset) in datasets_to_find_name]

        if filter.name == "has_stages":
            stages_to_find = [s for s in filter.param.split(",")]
            return [w for w in workflows if self._stages_contains(w.stages, stages_to_find)]

        return self._generic_execute_filter(workflows, filter)

    @classmethod
    def _date_compare(cls, date1: datetime, date2: datetime) -> bool:
        return date1.astimezone(timezone.utc) >= date2.astimezone(timezone.utc)

    @classmethod
    def _stages_contains(cls, stages: List[WFStage], stages_to_find: List[str]) -> bool:
        stage_ids = [str(s.id) for s in stages]
        return any(stage_to_find in stage_ids for stage_to_find in stages_to_find)
