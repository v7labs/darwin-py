from typing import List, Optional
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.data_objects.page import Page
from darwin.future.meta.objects.v7_id import V7ID


class ItemIDQuery(Query[V7ID]):
    def __init__(
        self,
        client: ClientCore,
        filters: Optional[List[QueryFilter]] = None,
        meta_params: Optional[Param] = None,
        page: Optional[Page] = None,
    ):
        super().__init__(client, filters, meta_params)
        self.page = page or Page.default()
        

    def _collect(self) -> List[UUID]:
        return []