from __future__ import annotations

from typing import Dict, List, Optional, Protocol, Union, cast
from uuid import UUID

from darwin.future.core.items.archive_items import archive_list_of_items
from darwin.future.core.items.assign_items import assign_items
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.core.items.restore_items import restore_list_of_items
from darwin.future.core.items.set_item_layout import set_item_layout
from darwin.future.core.items.set_item_priority import set_item_priority
from darwin.future.core.items.set_stage_to_items import set_stage_to_items
from darwin.future.core.items.tag_items import tag_items
from darwin.future.core.items.untag_items import untag_items
from darwin.future.data_objects.item import ItemCore, ItemLayout, ItemSlot
from darwin.future.data_objects.workflow import WFStageCore
from darwin.future.exceptions import BadRequest
from darwin.future.meta.objects.base import MetaBase


class hasStage(Protocol):
    # Using Protocol to avoid circular imports between item.py and stage.py
    _element: WFStageCore


class Item(MetaBase[ItemCore]):
    """
    Represents an item in a Darwin dataset.

    Args:
        MetaBase (Stage): Generic MetaBase object expanded by ItemCore object
            return type

    Attributes:
        name (str): The name of the item.
        id (UUID): The unique identifier of the item.
        slots (List[ItemSlot]): A list of slots associated with the item.
        path (str): The path of the item.
        dataset_id (int): The ID of the dataset the item belongs to.
        processing_status (str): The processing status of the item.
        archived (Optional[bool]): Whether the item is archived or not.
        priority (Optional[int]): The priority of the item.
        tags (Optional[Union[List[str], Dict[str, str]]]): The tags associated with the item.
        layout (Optional[ItemLayout]): The layout of the item.

    Methods:
        delete(self) -> None:
            Deletes the item from the Darwin dataset.

    Example usage:
        # Get the item object
        items = workflow.items.where(name='test').collect() # gets first page of items

        # Delete the items
        [item.delete() for item in items] # will collect all pages of items and delete individually

    """

    def delete(self) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        delete_list_of_items(self.client, team_slug, dataset_id, filters)

    def move_to_folder(self, path: str) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        move_list_of_items_to_folder(self.client, team_slug, dataset_id, path, filters)

    def set_priority(self, priority: int) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        set_item_priority(self.client, team_slug, dataset_id, priority, filters)

    def restore(self) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        restore_list_of_items(self.client, team_slug, dataset_id, filters)

    def archive(self) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        archive_list_of_items(self.client, team_slug, dataset_id, filters)

    def set_layout(self, layout: ItemLayout) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        assert isinstance(layout, ItemLayout)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        set_item_layout(self.client, team_slug, dataset_id, layout, filters)

    def assign(self, assignee_id: int, workflow_id: str | None = None) -> None:
        if not assignee_id:
            raise ValueError("Must specify assignee to assign items to")
        if not workflow_id:
            # if workflow_id is not specified, get it from the meta_params
            # this will be present in the case of a workflow object
            if "workflow_id" in self.meta_params:
                workflow_id = str(self.meta_params["workflow_id"])
            else:
                raise ValueError("Must specify workflow_id to set items to")
        assert isinstance(workflow_id, str)
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)

        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        assign_items(
            self.client, team_slug, dataset_id, assignee_id, workflow_id, filters
        )

    def tag(self, tag_id: int) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        if not isinstance(tag_id, int):
            raise BadRequest(f"tag_id must be an integer, got {type(tag_id)}")
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        tag_items(self.client, team_slug, dataset_id, tag_id, filters)

    def untag(self, tag_id: int) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)
        if not isinstance(tag_id, int):
            raise BadRequest(f"tag_id must be an integer, got {type(tag_id)}")
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        untag_items(self.client, team_slug, dataset_id, tag_id, filters)

    def set_stage(
        self, stage_or_stage_id: hasStage | str, workflow_id: str | None = None
    ) -> None:
        if not stage_or_stage_id:
            raise ValueError(
                "Must specify stage (either Stage object or stage_id string) to set items to"
            )
        if not workflow_id:
            # if workflow_id is not specified, get it from the meta_params
            # this will be present in the case of a workflow object
            if "workflow_id" in self.meta_params:
                workflow_id = str(self.meta_params["workflow_id"])
            else:
                raise ValueError("Must specify workflow_id to set items to")
        assert isinstance(workflow_id, str)
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            (
                self.meta_params["dataset_id"]
                if "dataset_id" in self.meta_params
                else self.meta_params["dataset_ids"]
            ),
        )
        assert isinstance(team_slug, str)

        # get stage_id from stage_or_stage_id
        if isinstance(stage_or_stage_id, str):
            stage_id = stage_or_stage_id
        else:
            stage_id = str(stage_or_stage_id._element.id)

        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        set_stage_to_items(
            self.client, team_slug, dataset_id, stage_id, workflow_id, filters
        )

    @property
    def name(self) -> str:
        return self._element.name

    @property
    def id(self) -> UUID:
        return self._element.id

    @property
    def slots(self) -> List[ItemSlot]:
        return self._element.slots

    @property
    def path(self) -> str:
        return self._element.path

    @property
    def dataset_id(self) -> int:
        return self._element.dataset_id

    @property
    def processing_status(self) -> str:
        return self._element.processing_status

    @property
    def archived(self) -> Optional[bool]:
        return self._element.archived

    @property
    def priority(self) -> Optional[int]:
        return self._element.priority

    @property
    def tags(self) -> Optional[Union[List[str], Dict[str, str]]]:
        return self._element.tags

    @property
    def layout(self) -> Optional[ItemLayout]:
        return self._element.layout

    def __str__(self) -> str:
        return f"Item\n\
- Item Name: {self._element.name}\n\
- Item Processing Status: {self._element.processing_status}\n\
- Item ID: {self._element.id}"
