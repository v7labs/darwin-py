from __future__ import annotations

from typing import Dict, Generic, List, Optional, TypeVar

from darwin.future.core.client import ClientCore
from darwin.future.pydantic_base import DefaultDarwin

R = TypeVar("R", bound=DefaultDarwin)
Param = Dict[str, object]


class MetaBase(Generic[R]):
    _element: R
    client: ClientCore

    def __init__(self, client: ClientCore, element: R, meta_params: Optional[Param] = None) -> None:
        self.client = client
        self._element = element
        self.meta_params = meta_params or dict()

    def __str__(self) -> str:
        return str(self._element)
