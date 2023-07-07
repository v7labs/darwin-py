from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from darwin.future.core.client import Client
from darwin.future.pydantic_base import DefaultDarwin

R = TypeVar("R", bound=DefaultDarwin)


class MetaBase(Generic[R]):
    _item: Optional[R]
    client: Client

    def __init__(self, client: Client, item: Optional[R] = None) -> None:
        self.client = client
        self._item = item

    def __str__(self) -> str:
        if self._item is None:
            raise ValueError("MetaBase has no item")
        return str(self._item)
