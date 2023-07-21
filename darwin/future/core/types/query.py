from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
    overload,
)

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

    @classmethod
    def _from_dict(cls, d: Dict[str, Any]) -> QueryFilter:  # type: ignore
        if "name" not in d or "param" not in d:
            raise ValueError(f"args must be a QueryFilter or a dict with 'name' and 'param' keys, got {d}")
        modifier = Modifier(d["modifier"]) if "modifier" in d else None
        return QueryFilter(name=d["name"], param=str(d["param"]), modifier=modifier)

    @classmethod
    def _from_args(cls, *args: object, **kwargs: str) -> List[QueryFilter]:
        filters = []
        for arg in args:
            filters.append(cls._from_arg(arg))
        for key, value in kwargs.items():
            filters.append(cls._from_kwarg(key, value))
        return filters

    @classmethod
    def _from_arg(cls, arg: object) -> QueryFilter:
        if isinstance(arg, QueryFilter):
            return arg
        elif isinstance(arg, dict):
            return cls._from_dict(arg)
        else:
            raise ValueError(f"args must be a QueryFilter or a dict with 'name' and 'param' keys, got {arg}")

    @classmethod
    def _from_kwarg(cls, key: str, value: str) -> QueryFilter:
        if ":" in value:
            modifier_str, value = value.split(":", 1)
            modifier = Modifier(modifier_str)
        else:
            modifier = None
        return QueryFilter(name=key, param=value, modifier=modifier)


class Query(Generic[T], ABC):
    """Basic Query object with methods to manage filters
    Methods:
        filter: adds a filter to the query object, returns a new query object
        where: Applies a filter on the query object, returns a new query object
        collect: Executes the query on the client and returns the results
        _generic_execute_filter: Executes a filter on a list of objects
    """

    def __init__(
        self, client: Client, filters: Optional[List[QueryFilter]] = None, meta_params: Optional[Param] = None
    ):
        self.meta_params = meta_params
        self.client = client
        self.filters = filters
        self.results: Optional[List[T]] = None

    def filter(self, filter: QueryFilter) -> Query[T]:
        return self + filter

    def __add__(self, filter: QueryFilter) -> Query[T]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            self.filters = []
        return self.__class__(self.client, filters=[*self.filters, filter], meta_params=self.meta_params)

    def __sub__(self, filter: QueryFilter) -> Query[T]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            return self
        return self.__class__(
            self.client, filters=[f for f in self.filters if f != filter], meta_params=self.meta_params
        )

    def __iadd__(self, filter: QueryFilter) -> Query[T]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            self.filters = [filter]
            return self
        self.filters.append(filter)
        return self

    def __isub__(self, filter: QueryFilter) -> Query[T]:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            return self
        self.filters = [f for f in self.filters if f != filter]
        return self

    def __len__(self) -> int:
        if self.results is None:
            self.results = list(self.collect())
        return len(self.results)

    def __iter__(self) -> Query[T]:
        self.n = 0
        return self

    def __next__(self) -> T:
        if self.results is None:
            self.results = list(self.collect())
        if self.n < len(self.results):
            result = self.results[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

    def __getitem__(self, index: int) -> T:
        if self.results is None:
            self.results = list(self.collect())
        return self.results[index]

    def __setitem__(self, index: int, value: T) -> None:
        if self.results is None:
            self.results = list(self.collect())
        self.results[index] = value

    def where(self, *args: object, **kwargs: str) -> Query[T]:
        filters = QueryFilter._from_args(*args, **kwargs)
        for item in filters:
            self += item
        return self

    @abstractmethod
    def collect(self) -> List[T]:
        raise NotImplementedError("Not implemented")

    def collect_one(self) -> T:
        if self.results is None:
            self.results = list(self.collect())
        if len(self.results) == 0:
            raise ValueError("No results found")
        if len(self.results) > 1:
            raise ValueError("More than one result found")
        return self.results[0]

    def first(self) -> Optional[T]:
        if self.results is None:
            self.results = list(self.collect())
        if len(self.results) == 0:
            return None
        return self.results[0]

    def _generic_execute_filter(self, objects: List[T], filter: QueryFilter) -> List[T]:
        return [m for m in objects if filter.filter_attr(getattr(m._item, filter.name))]
