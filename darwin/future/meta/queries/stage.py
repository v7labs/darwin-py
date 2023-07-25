from __future__ import annotations

from typing import List
from uuid import UUID

from darwin.future.core.client import Client
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.core.workflows.get_workflow import get_workflow
from darwin.future.meta.objects.stage import StageMeta


class StageQuery(Query[StageMeta]):
    def collect(self) -> List[StageMeta]:
        if not self.meta_params:
            raise ValueError("Must specify workflow_id to query stages")
        workflow_id: UUID = self.meta_params["workflow_id"]
        meta_params = self.meta_params
        workflow, exceptions = get_workflow(self.client, str(workflow_id))
        assert workflow is not None
        stages = [StageMeta(self.client, s, meta_params=meta_params) for s in workflow.stages]
        if not self.filters:
            self.filters = []
        for filter in self.filters:
            stages = self._execute_filter(stages, filter)
        return stages

    def _execute_filter(self, stages: List[StageMeta], filter: QueryFilter) -> List[StageMeta]:
        """Executes filtering on the local list of stages
        Parameters
        ----------
        stages : List[Stage]
        filter : QueryFilter

        Returns
        -------
        List[Stage]: Filtered subset of stages
        """
        if filter.name == "role":
            return [s for s in stages if s._item is not None and filter.filter_attr(s._item.type.value)]
        return super()._generic_execute_filter(stages, filter)
