from __future__ import annotations

from functools import reduce
from typing import Dict, Literal, Protocol, Union

from darwin.future.core.items.archive_items import archive_list_of_items
from darwin.future.core.items.assign_items import assign_items
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.core.items.get import list_items, list_items_unstable
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.core.items.restore_items import restore_list_of_items
from darwin.future.core.items.set_item_layout import set_item_layout
from darwin.future.core.items.set_item_priority import set_item_priority
from darwin.future.core.items.set_stage_to_items import set_stage_to_items
from darwin.future.core.items.tag_items import tag_items
from darwin.future.core.items.untag_items import untag_items
from darwin.future.core.types.common import JSONDict, QueryString
from darwin.future.core.types.query import PaginatedQuery, QueryFilter
from darwin.future.data_objects.advanced_filters import GroupFilter, SubjectFilter
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
        params = self._build_params()
        if isinstance(params, QueryString):
            items_core, errors = list_items(self.client, team_slug, dataset_ids, params)
        else:
            items_core, errors = list_items_unstable(
                api_client=self.client, team_slug=team_slug, params=params
            )
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

    def move_to_folder(self, path: str) -> None:
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

    def _build_params(self) -> Union[QueryString, JSONDict]:
        if self._advanced_filters is None:
            return reduce(
                lambda s1, s2: s1 + s2,
                [
                    self.page.to_query_string(),
                    *[QueryString(f.to_dict()) for f in self.filters],
                ],
            )
        if not self.meta_params["dataset_ids"] and not self.meta_params["dataset_id"]:
            raise ValueError("Must specify dataset_ids to query items")
        dataset_id = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        return {
            "dataset_ids": [dataset_id],
            "page": self.page.model_dump(),
            "filter": self._advanced_filters.model_dump(),
        }

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

    def assign(self, assignee_id: int, workflow_id: str | None = None) -> None:
        if not assignee_id:
            raise ValueError("Must specify assignee to assign items to")

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

        dataset_ids = (
            self.meta_params["dataset_ids"]
            if "dataset_ids" in self.meta_params
            else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}

        assign_items(
            self.client, team_slug, dataset_ids, assignee_id, workflow_id, filters
        )

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

    def where(
        self,
        *args: GroupFilter | SubjectFilter,
        _operator: Literal["and", "or"] = "and",
        **kwargs: str,
    ) -> ItemQuery:
        """Adds a filter to the query
        This can be used with simple filters via a keyword argument
        or with advanced filters via a GroupFilter or SubjectFilter object as args.

        Args:
            _operator (Literal["and", "or"], optional): The operator to use when combining

        Raises:
            ValueError: Raises if trying to use both simple and advanced filters

        Returns:
            ItemQuery: Self
        """
        if len(args) > 0 and len(kwargs) > 0:
            raise ValueError("Cannot specify both args and kwargs")
        if len(kwargs) > 1:
            return super().where(**kwargs)
        arg_list = list(args)
        if self._advanced_filters is None:
            self._advanced_filters = arg_list.pop(0)
        for arg in arg_list:
            if _operator == "and":
                self._advanced_filters = self._advanced_filters & arg
            if _operator == "or":
                self._advanced_filters = self._advanced_filters | arg
        return self
