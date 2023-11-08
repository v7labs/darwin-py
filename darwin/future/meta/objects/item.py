from __future__ import annotations

from typing import Dict, List, Optional, Union
from uuid import UUID

from darwin.future.data_objects.item import ItemCore, ItemLayout, ItemSlot
from darwin.future.meta.objects.base import MetaBase


class Item(MetaBase[ItemCore]):

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
