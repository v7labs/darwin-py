from typing import List, Optional
from uuid import UUID

from darwin.future.core.client import Client
from darwin.future.core.workflows.get_workflow import get_workflow
from darwin.future.data_objects.workflow import WFStage
from darwin.future.meta.objects.base import MetaBase


class StageMeta(MetaBase[WFStage]):
    """_summary_

    Args:
        MetaBase (_type_): _description_
    """
