from __future__ import annotations

import asyncio
import logging
from functools import reduce
from typing import Dict, List, overload

from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.core.items.get import list_items
from darwin.future.core.items.move_items_to_folder import move_list_of_items_to_folder
from darwin.future.core.types.common import QueryString
from darwin.future.core.types.query import PaginatedQuery
from darwin.future.data_objects.item import ItemCreate
from darwin.future.meta.meta_uploader import combined_uploader
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.meta.objects.item import Item

logger = logging.getLogger(__name__)


class ItemQuery(PaginatedQuery[Item]):
    def _collect(self) -> Dict[int, Item]:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if "dataset_ids" not in self.meta_params and "dataset_id" not in self.meta_params:
            raise ValueError("Must specify dataset_ids to query items")
        dataset_ids = (
            self.meta_params["dataset_ids"] if "dataset_ids" in self.meta_params else self.meta_params["dataset_id"]
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
            i + offset: Item(client=self.client, element=item, meta_params=self.meta_params)
            for i, item in enumerate(items_core)
        }
        return items

    def delete(self) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if "dataset_ids" not in self.meta_params and "dataset_id" not in self.meta_params:
            raise ValueError("Must specify dataset_ids to query items")
        dataset_ids = (
            self.meta_params["dataset_ids"] if "dataset_ids" in self.meta_params else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        delete_list_of_items(self.client, team_slug, dataset_ids, filters)

    def move_to_folder(self, path) -> None:
        if "team_slug" not in self.meta_params:
            raise ValueError("Must specify team_slug to query items")
        if "dataset_ids" not in self.meta_params and "dataset_id" not in self.meta_params:
            raise ValueError("Must specify dataset_ids to query items")
        if not path:
            raise ValueError("Must specify path to move items to")
        dataset_ids = (
            self.meta_params["dataset_ids"] if "dataset_ids" in self.meta_params else self.meta_params["dataset_id"]
        )
        team_slug = self.meta_params["team_slug"]
        self.collect_all()
        ids = [item.id for item in self]
        filters = {"item_ids": [str(item) for item in ids]}
        move_list_of_items_to_folder(self.client, team_slug, dataset_ids, path, filters)

    @overload
    def new(
        self,
        item_payload: ItemCreate,
        dataset: int,
    ) -> Item | List[Item]:
        ...

    @overload
    def new(
        self,
        item_payload: ItemCreate,
    ) -> Item | List[Item]:
        ...

    def new(
        self,
        item_payload: ItemCreate,
        dataset: int | None = None,
    ) -> Item | List[Item]:
        """
        Synchronously creates a new item/items in a Darwin dataset.

        Parameters
        ----------
        item_payload : ItemCreate
            The item payload to create the item with.
        use_folders : bool
            Whether to use folders (preserve the folder structure of paths) or not.
        force_slots : bool (Not yet implemented)
            Whether to force slots or not.
        callback_when_loaded : LoadedCallbackType
            Callback to run when the item or items is/are loaded.
        callback_when_complete : CompleteCallbackType
            Callback to run when the item or items is/are complete.

        Returns
        """
        loop = asyncio.get_event_loop()

        return loop.run_until_complete(
            self.new_async(
                item_payload=item_payload,
            )
        )

    @overload
    async def new_async(
        self,
        item_payload: ItemCreate,
        dataset: int,
    ) -> Item | List[Item]:
        ...

    @overload
    async def new_async(
        self,
        item_payload: ItemCreate,
    ) -> Item | List[Item]:
        ...

    async def new_async(
        self,
        item_payload: ItemCreate,
        dataset: int | None = None,
    ) -> Item | List[Item]:
        """
        Asynchronously creates a new item/items in a Darwin dataset.

        Parameters
        ----------
        item_payload : ItemCreate
            The item payload to create the item with.
        use_folders : bool
            Whether to use folders (preserve the folder structure of paths) or not.
        force_slots : bool (Not yet implemented)
            Whether to force slots or not.
        callback_when_loaded : LoadedCallbackType
            Callback to run when the item or items is/are loaded.
        callback_when_complete : CompleteCallbackType
            Callback to run when the item or items is/are complete.

        Returns
        -------
        Item | List[Item]
            The item or items created.
        """
        dataset_id = self.meta_params.get("dataset_id")
        team_slug = self.meta_params.get("team_slug")

        is_called_with_dataset = dataset is not None
        is_called_from_dataset = dataset_id is not None

        if is_called_with_dataset and is_called_from_dataset:
            raise ValueError("Cannot specify dataset and when calling from a dataset")

        if not is_called_with_dataset and not is_called_from_dataset:
            raise ValueError("Must specify dataset to query items")

        if not isinstance(team_slug, str):
            raise ValueError("Must have team_slug to query items")

        if not is_called_from_dataset:
            dataset_id = dataset

        assert isinstance(dataset_id, int)

        return await combined_uploader(
            client=self.client,
            dataset_id=dataset_id,
            item_payload=item_payload,
        )
