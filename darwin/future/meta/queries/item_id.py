from functools import reduce
from typing import Dict, List, Optional
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.items.get import get_item_ids
from darwin.future.core.types.common import QueryString
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.data_objects.page import Page
from darwin.future.meta.objects.v7_id import V7ID


class ItemIDQuery(Query[V7ID]):
    def __init__(
        self,
        client: ClientCore,
        filters: Optional[List[QueryFilter]] = None,
        meta_params: Optional[Param] = None,
        page: Page = Page.default(),
    ):
        super().__init__(client, filters, meta_params)
        self.page = page
        

    def _collect(self) -> Dict[int, UUID]:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query item ids")
        if "dataset_id" not in self.meta_params:
            raise ValueError("Must specify dataset_id to query item ids")
        assert self.page.offset is not None
        assert self.page.size is not None
        team_slug: str = self.meta_params["team_slug"]
        dataset_id: int = self.meta_params["dataset_id"]
        params: QueryString = reduce(lambda s1, s2: s1 + s2, [self.page.to_query_string(), *self.filters])
        uuids = get_item_ids(self.client, team_slug, dataset_id, params)
        
        results = {x: uuids[i] for i, x in enumerate(range(self.page.offset, self.page.offset + self.page.size))}
        self.page.increment()
        return results
    