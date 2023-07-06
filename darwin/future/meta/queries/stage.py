from __future__ import annotations

from typing import List

from darwin.future.core.client import Client
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.core.workflows.get_workflows import get_workflows
from darwin.future.meta.objects.stage import StageMeta


class StageQuery(Query[StageMeta]):
    def where(self, param: Param) -> StageQuery:
        filter = QueryFilter.parse_obj(param)
        query = self + filter

        return StageQuery(self.client, query.filters)

    def collect(self) -> List[StageMeta]:
        workflows = get_workflows(self.client)
        stages = []
        for workflow in workflows:
            stages.append(StageMeta(self.client, workflow.id, workflow.stages))

        if not self.filters:
            self.filters = []
        for filter in self.filters:
            stages = self._execute_filter(stages, filter)
