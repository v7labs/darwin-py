from __future__ import annotations

from typing import Dict, List, Literal, Optional, Union, cast
from uuid import UUID

from darwin.future.core.items.delete_items import delete_list_of_items
from darwin.future.data_objects.item import ItemCore, ItemLayout, ItemSlot
from darwin.future.meta.objects.base import MetaBase


class Item(MetaBase[ItemCore]):
    def delete(self) -> None:
        team_slug, dataset_id = (
            self.meta_params["team_slug"],
            self.meta_params["dataset_id"],
        )
        assert isinstance(team_slug, str)
        assert isinstance(dataset_id, (int, list, str))
        if isinstance(dataset_id, list):
            dataset_id = cast(List[int], dataset_id)
        if isinstance(dataset_id, str):
            assert dataset_id == "all"
            dataset_id = cast(Literal["all"], dataset_id)
        delete_list_of_items(self.client, team_slug, dataset_id, [self.id])

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
