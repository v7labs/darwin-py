from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Mapping, Optional, TypeVar

from darwin.future.core.client import Client
from darwin.future.meta.objects.base import MetaBase
from darwin.future.pydantic_base import DefaultDarwin

T = TypeVar("T", bound=MetaBase)
R = TypeVar("R", bound=DefaultDarwin)
Param = Dict[str, Any]  # type: ignore


class Modifier(Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    NOT_EQUAL = "!="
    CONTAINS = "contains"


class QueryFilter(DefaultDarwin):
    """Basic query filter with a name and a parameter

    Attributes
    ----------
    name: str
    param: str
    modifier: Optional[Modifiers]: Optional modifier to apply to the filter
    """

    name: str
    param: str
    modifier: Optional[Modifier] = None

    def filter_attr(self, attr: Any) -> bool:  # type: ignore
        caster: Callable[[str], Any] = type(attr)  # type: ignore
        param = caster(self.param)  # attempt to cast the param to the type of the attribute
        if self.modifier is None:
            return attr == param
        elif self.modifier == Modifier.GREATER_EQUAL:
            return attr >= param
        elif self.modifier == Modifier.GREATER_THAN:
            return attr > param
        elif self.modifier == Modifier.LESS_EQUAL:
            return attr <= param
        elif self.modifier == Modifier.LESS_THAN:
            return attr < param
        elif self.modifier == Modifier.NOT_EQUAL:
            return attr != param
        elif self.modifier == Modifier.CONTAINS:
            return param in attr
        else:
            raise ValueError(f"Unknown modifier {self.modifier}")


class Query(Generic[T, R], ABC):
    """Basic Query object with methods to manage filters
    Methods:
        filter: adds a filter to the query object, returns a new query object
        where: Applies a filter on the query object, returns a new query object
        collect: Executes the query on the client and returns the results
        _generic_execute_filter: Executes a filter on a list of objects
    """

    def __init__(self, client: Client, filters: Optional[List[QueryFilter]] = None):
        self.client = client
        self.filters = filters
        self.results: Optional[List[R]] = None

    def filter(self, filter: QueryFilter) -> Query[T, R]:
        return self + filter

    def __add__(self, filter: QueryFilter) -> Query[T, R]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            self.filters = []
        return self.__class__(self.client, [*self.filters, filter])

    def __sub__(self, filter: QueryFilter) -> Query[T, R]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            return self
        return self.__class__(self.client, [f for f in self.filters if f != filter])

    def __iadd__(self, filter: QueryFilter) -> Query[T, R]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            self.filters = [filter]
            return self
        self.filters.append(filter)
        return self

    def __isub__(self, filter: QueryFilter) -> Query[T, R]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            return self
        self.filters = [f for f in self.filters if f != filter]
        return self

    def __len__(self) -> int:
        if self.filters is None:
            return 0
        return len(self.filters)

    def __iter__(self) -> Query[T, R]:
        self.n = 0
        return self

    def __next__(self) -> R:
        if self.results is None:
            self.results = list(self.collect())
        if self.n < len(self.results):
            result = self.results[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration
        
    def __getitem__(self, index: int) -> R:
        if self.results is None:
            self.results = list(self.collect())
        return self.results[index]
    
    def __setitem__(self, index: int, value: R) -> None:
        if self.results is None:
            self.results = list(self.collect())
        self.results[index] = value

    @abstractmethod
    def where(self, param: Param) -> Query[T, R]:
        raise NotImplementedError("Not implemented")

    @abstractmethod
    def collect(self) -> T:
        raise NotImplementedError("Not implemented")

    def _generic_execute_filter(self, objects: List[R], filter: QueryFilter) -> List[R]:
        return [m for m in objects if filter.filter_attr(getattr(m, filter.name))]

