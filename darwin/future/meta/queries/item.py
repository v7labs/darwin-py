from functools import reduce
from typing import Dict

from darwin.future.core.items.get import list_items
from darwin.future.core.types.common import QueryString
from darwin.future.core.types.query import PaginatedQuery
from darwin.future.meta.objects.item import Item


class ItemQuery(PaginatedQuery[Item]):
    def _collect(self) -> Dict[int, Item]:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            or "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        params: QueryString = reduce(
            lambda s1, s2: s1 + s2,
            [
                self.page.to_query_string(),
                *[QueryString(f.to_dict()) for f in self.filters],
            ],
        )
        items_core, errors = list_items(self.client, team_slug, dataset_ids, params)
        offset = self.page.offset
        items = {
            i
            + offset: Item(
                client=self.client, element=item, meta_params=self.meta_params
            )
            for i, item in enumerate(items_core)
        }
        return items
