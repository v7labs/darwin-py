from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Union, cast
from uuid import UUID

from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.data_objects.item import (
    CompleteCallbackType,
    ItemCore,
    ItemCreate,
    ItemLayout,
    ItemSlot,
    LoadedCallbackType,
)
from darwin.future.meta.meta_uploader import combined_uploader
from darwin.future.meta.objects.base import MetaBase


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
            self.meta_params["dataset_id"] if "dataset_id" in self.meta_params else self.meta_params["dataset_ids"],
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        delete_list_of_items(self.client, team_slug, dataset_id, filters)

    def move_to_folder(self, path: str) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            self.meta_params["dataset_id"] if "dataset_id" in self.meta_params else self.meta_params["dataset_ids"],
        )
        assert isinstance(team_slug, str)
        dataset_id = cast(Union[int, List[int]], dataset_id)
        filters = {"item_ids": [str(self.id)]}
        move_list_of_items_to_folder(self.client, team_slug, dataset_id, path, filters)

    def new(
        self,
        item_payload: ItemCreate,
        use_folders=False,
        force_slots=False,
        callback_when_loaded=LoadedCallbackType,
        callback_when_complete=CompleteCallbackType,
    ) -> Item | List[Item]:
        """
        Synchronously creates a new item/items in a Darwin dataset.

        @TODO: Add docstring
        """
        loop = asyncio.get_event_loop()

        return loop.run_until_complete(
            self.new_async(
                item_payload=item_payload,
                use_folders=use_folders,
                force_slots=force_slots,
                callback_when_loaded=callback_when_loaded,
                callback_when_complete=callback_when_complete,
            )
        )

    async def new_async(
        self,
        item_payload: ItemCreate,
        use_folders=False,
        force_slots=False,
        callback_when_loaded=LoadedCallbackType,
        callback_when_complete=LoadedCallbackType,
    ) -> Item | List[Item]:
        """
        Asynchronously creates a new item/items in a Darwin dataset.
        @TODO: Add docstring
        """
        dataset_id = self.meta_params.get("dataset_id")
        team_slug = self.meta_params.get("team_slug")
        assert isinstance(team_slug, str), "Must specify team_slug to query items"
        assert dataset_id, "Must specify dataset_id to create items"

        dataset_id = cast(int, dataset_id)
        dataset = get_dataset(self.client, str(dataset_id))

        upload_items = await combined_uploader(
            client=self.client,
            dataset=dataset,
            item_payload=item_payload,
            use_folders=use_folders,
            force_slots=force_slots,
            callback_when_loaded=callback_when_loaded,
            callback_when_complete=callback_when_complete,
        )

        return [
            Item(
                client=self.client,
                element=ItemCore(
                    # TODO: Add ItemCore object
                ),
                meta_params=self.meta_params,
            )
            for item in upload_items
        ]

        # Create items from ItemUpload objects

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
