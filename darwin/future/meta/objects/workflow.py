from uuid import UUID

from darwin.future.data_objects.workflow import Workflow
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery


class WorkflowMeta(MetaBase[Workflow]):
    @property
    def stages(self) -> StageQuery:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        meta_params = {"workflow_id": self._item.id}
        return StageQuery(self.client, meta_params=meta_params)

    @property
    def id(self) -> UUID:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        return self._item.id

    @property
    def name(self) -> str:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        return self._item.name