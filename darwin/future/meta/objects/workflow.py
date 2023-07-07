from typing import List, Optional

from darwin.client import Client
from darwin.future.data_objects.workflow import Workflow
from darwin.future.meta.objects.base import MetaBase


class WorkflowMeta(MetaBase[Workflow]):
    """WorkflowMeta object with methods to manage filters, retrieve data, and execute
    filters

    #TODO Placeholder to make other code work pending this


    """

    client: Client

    def __init__(self, client: Client, workflows: Optional[List[Workflow]]):
        self.client = client
        super().__init__(workflows)

    # TODO Meta CRUD
