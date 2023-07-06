from darwin.future.data_objects.workflow import Workflow
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery


class MetaWorkflow(MetaBase[Workflow]):
    @property
    def stages(self) -> StageQuery:
        return StageQuery(self.client)
