from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from darwin.future.core.client import ClientCore
from darwin.future.exceptions import (
    InvalidQueryFilter,
    InvalidQueryModifier,
    MoreThanOneResultFound,
    ResultsNotFound,
)
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
        param = caster(
            self.param
        )  # attempt to cast the param to the type of the attribute
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
            raise InvalidQueryModifier(f"Unknown modifier {self.modifier}")

    @classmethod
    def _from_dict(cls, d: Dict[str, Any]) -> QueryFilter:  # type: ignore
        if "name" not in d or "param" not in d:
            raise InvalidQueryFilter(
                "args must be a QueryFilter or a dict with 'name' and 'param' keys,"
                f" got {d}"
            )
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
            raise InvalidQueryFilter(
                "args must be a QueryFilter or a dict with 'name' and 'param' keys,"
                f" got {arg}"
            )

    @classmethod
    def _from_kwarg(cls, key: str, value: str) -> QueryFilter:
        if ":" in value:
            modifier_str, value = value.split(":", 1)
            modifier = Modifier(modifier_str)
        else:
            modifier = None
        return QueryFilter(name=key, param=value, modifier=modifier)


class Query(Generic[T], ABC):
    """
    A basic Query object with methods to manage filters. This is an abstract class not
    meant to be used directly. Use a subclass instead, like DatasetQuery.
    This class will lazy load results and cache them internally, and allows for filtering
    of the objects locally by default. To execute the query, call the collect() method,
    or iterate over the query object.

    Attributes:
        meta_params (dict): A dictionary of metadata parameters.
        client (ClientCore): The client used to execute the query.
        filters (List[QueryFilter]): A list of QueryFilter objects used to filter the query results.
        results (List[T]): A list of query results, cached internally for iterable access.
        _changed_since_last (bool): A boolean indicating whether the query has changed since the last execution.

    Methods:
        filter(name: str, param: str, modifier: Optional[Modifier] = None) -> Query[T]:
            Adds a filter to the query object and returns a new query object.
        where(name: str, param: str, modifier: Optional[Modifier] = None) -> Query[T]:
            Applies a filter on the query object and returns a new query object.
        first() -> Optional[T]:
            Returns the first result of the query. Raises an exception if no results are found.
        collect() -> List[T]:
            Executes the query on the client and returns the results. Raises an exception if no results are found.
        _generic_execute_filter(objects: List[T], filter_: QueryFilter) -> List[T]:
            Executes a filter on a list of objects. Locally by default, but can be overwritten by subclasses.

    Examples:
        # Create a query object
        # DatasetQuery is linked to the object it returns, Dataset, and is iterable
        # overwrite the _collect() method to execute insantiate this object
        Class DatasetQuery(Query[Dataset]):
            ...

        # Intended usage via chaining
        # where client.team.datasets returns a DatasetQuery object and can be chained
        # further with multiple where calls before collecting
        datasets = client.team.datasets.where(...).where(...).collect()
    """

    def __init__(
        self,
        client: ClientCore,
        filters: Optional[List[QueryFilter]] = None,
        meta_params: Optional[Param] = None,
    ):
        self.meta_params: dict = meta_params or {}
        self.client = client
        self.filters = filters or []
        self.results: Optional[List[T]] = None
        self._changed_since_last: bool = True

    def filter(self, filter: QueryFilter) -> Query[T]:
        return self + filter

    def __add__(self, filter: QueryFilter) -> Query[T]:
        self._changed_since_last = True
        return self.__class__(
            self.client, filters=[*self.filters, filter], meta_params=self.meta_params
        )

    def __sub__(self, filter: QueryFilter) -> Query[T]:
        self._changed_since_last = True
        return self.__class__(
            self.client,
            filters=[f for f in self.filters if f != filter],
            meta_params=self.meta_params,
        )

    def __iadd__(self, filter: QueryFilter) -> Query[T]:
        self.filters.append(filter)
        self._changed_since_last = True
        return self

    def __isub__(self, filter: QueryFilter) -> Query[T]:
        self.filters = [f for f in self.filters if f != filter]
        self._changed_since_last = True
        return self

    def __len__(self) -> int:
        if not self.results:
            self.results = list(self._collect())
        return len(self.results)

    def __iter__(self) -> Query[T]:
        self.n = 0
        return self

    def __next__(self) -> T:
        if not self.results:
            self.results = list(self._collect())
        if self.n < len(self.results):
            result = self.results[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

    def __getitem__(self, index: int) -> T:
        if not self.results:
            self.results = list(self._collect())
        return self.results[index]

    def __setitem__(self, index: int, value: T) -> None:
        if not self.results:
            self.results = list(self._collect())
        self.results[index] = value

    def where(self, *args: object, **kwargs: str) -> Query[T]:
        filters = QueryFilter._from_args(*args, **kwargs)
        for item in filters:
            self += item
        self._changed_since_last = True
        return self

    def collect(self, force: bool = False) -> List[T]:
        if force or self._changed_since_last:
            self.results = []
        self.results = self._collect()
        self._changed_since_last = False
        return self.results

    @abstractmethod
    def _collect(self) -> List[T]:
        raise NotImplementedError("Not implemented")

    def collect_one(self) -> T:
        if not self.results:
            self.results = list(self.collect())
        if len(self.results) == 0:
            raise ResultsNotFound("No results found")
        if len(self.results) > 1:
            raise MoreThanOneResultFound("More than one result found")
        return self.results[0]

    def first(self) -> T:
        if not self.results:
            self.results = list(self.collect())
        if len(self.results) == 0:
            raise ResultsNotFound("No results found")
        return self.results[0]

    def _generic_execute_filter(self, objects: List[T], filter: QueryFilter) -> List[T]:
        return [
            m for m in objects if filter.filter_attr(getattr(m._element, filter.name))
        ]
