from __future__ import annotations

from functools import reduce
from typing import Dict, Protocol

from darwin.future.core.items.archive_items import archive_list_of_items
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.core.items.get import list_items
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.core.items.restore_items import restore_list_of_items
from darwin.future.core.items.set_item_layout import set_item_layout
from darwin.future.core.items.set_item_priority import set_item_priority
from darwin.future.core.items.set_stage_to_items import set_stage_to_items
from darwin.future.core.items.tag_items import tag_items
from darwin.future.core.items.untag_items import untag_items
from darwin.future.core.types.common import QueryString
from darwin.future.core.types.query import PaginatedQuery, QueryFilter
from darwin.future.data_objects.item import ItemLayout
from darwin.future.data_objects.sorting import SortingMethods
from darwin.future.data_objects.workflow import WFStageCore
from darwin.future.exceptions import BadRequest
from darwin.future.meta.objects.item import Item


class hasStage(Protocol):
    # Using Protocol to avoid circular imports between item.py and stage.py
    _element: WFStageCore


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

    def sort(self, **kwargs: str) -> ItemQuery:
        valid_values = {"asc", "desc"}
        for value in kwargs.values():
            if value not in valid_values:
                raise ValueError(
                    f"Invalid sort value: {value}. Must be one of {valid_values}."
                )
        sorting_methods = SortingMethods(**kwargs)  # type: ignore
        for key, value in sorting_methods.dict().items():
            if value is not None:
                filter = QueryFilter(name=f"sort[{key}]", param=value)
                self.filters.append(filter)
        return self

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

    def set_layout(self, layout: ItemLayout) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")

        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")

        assert isinstance(layout, ItemLayout)
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        set_item_layout(self.client, team_slug, dataset_ids, layout, filters)

    def tag(self, tag_id: int) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        if not tag_id:
            raise ValueError("Must specify tag_id to tag items with")
        if not isinstance(tag_id, int):
            raise BadRequest(f"tag_id must be an integer, got {type(tag_id)}")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        tag_items(self.client, team_slug, dataset_ids, tag_id, filters)

    def untag(self, tag_id: int) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        if not tag_id:
            raise ValueError("Must specify tag_id to untag items with")
        if not isinstance(tag_id, int):
            raise BadRequest(f"tag_id must be an integer, got {type(tag_id)}")
        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        untag_items(self.client, team_slug, dataset_ids, tag_id, filters)

    def set_stage(
        self, stage_or_stage_id: hasStage | str, workflow_id: str | None = None
    ) -> None:
        if not stage_or_stage_id:
            raise ValueError(
                "Must specify stage (either Stage object or stage_id string) to set items to"
            )

        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if (
            "dataset_ids" not in self.meta_params
            and "dataset_id" not in self.meta_params
        ):
            raise ValueError("Must specify dataset_ids to query items")
        if not workflow_id:
            # if workflow_id is not specified, get it from the meta_params
            # this will be present in the case of a workflow object
            if "workflow_id" in self.meta_params:
                workflow_id = str(self.meta_params["workflow_id"])
            else:
                raise ValueError("Must specify workflow_id to set items to")
        assert isinstance(workflow_id, str)
        if not stage_or_stage_id:
            raise ValueError("Must specify stage to set stage for items")

        # get stage_id from stage_or_stage_id
        if isinstance(stage_or_stage_id, str):
            stage_id = stage_or_stage_id
        else:
            stage_id = str(stage_or_stage_id._element.id)

        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}

        set_stage_to_items(
            self.client, team_slug, dataset_ids, stage_id, workflow_id, filters
        )
