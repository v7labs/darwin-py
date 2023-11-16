from functools import reduce
from typing import Dict

from darwin.future.core.items.archive_items import archive_list_of_items
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.core.items.get import list_items
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.core.items.set_item_priority import set_item_priority
from darwin.future.core.items.restore_items import restore_list_of_items
from darwin.future.core.types.common import QueryString
from darwin.future.core.types.query import PaginatedQuery
from darwin.future.meta.objects.item import Item


class ItemQuery(PaginatedQuery[Item]):
    def _collect(self) -> Dict[int, Item]:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
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

    def delete(self) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        delete_list_of_items(self.client, team_slug, dataset_ids, filters)

    def move_to_folder(self, path) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        if not path:
            raise ValueError("Must specify path to move items to")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        move_list_of_items_to_folder(self.client, team_slug, dataset_ids, path, filters)

    def set_priority(self, priority: int) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        if not priority:
            raise ValueError("Must specify priority to set items to")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        set_item_priority(self.client, team_slug, dataset_ids, priority, filters)

    def restore(self) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        restore_list_of_items(self.client, team_slug, dataset_ids, filters)

    def archive(self) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        archive_list_of_items(self.client, team_slug, dataset_ids, filters)
