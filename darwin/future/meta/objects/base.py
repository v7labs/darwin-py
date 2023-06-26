from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

from darwin.future.pydantic_base import DefaultDarwin

R = TypeVar("R", bound=DefaultDarwin)

class MetaBase(Generic[R]):
    def __init__(self, items: Optional[List[R]]=None) -> None:
        self._items = items
    
    def __getitem__(self, index: int) -> R:
        if self._items is None:
            self._items = []
        return self._items[index]
    
    def __setitem__(self, index: int, value: R) -> None:
        if self._items is None:
            self._items = []
        self._items[index] = value
    
    def __iter__(self) -> MetaBase[R]:
        self.n = 0
        return self
    
    def __next__(self) -> R:
        if self._items is None:
            self._items = []
        if self.n < len(self._items):
            result = self._items[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration
        
    def __len__(self) -> int:
        if self._items is None:
            self._items = []
        return len(self._items)