from typing import Optional
from uuid import UUID

from darwin.future.core.client import Client
from darwin.future.data_objects.workflow import WFStage
from darwin.future.meta.objects.base import MetaBase


class StageMeta(MetaBase[WFStage]):
    """_summary_

    Args:
        MetaBase (_type_): _description_
    """

    def __init__(
        self,
        client: Client,
        item: Optional[WFStage] = None,
        workflow_id: Optional[UUID] = None,
    ) -> None:
        self._workflow_id = workflow_id
        super().__init__(client, item)
