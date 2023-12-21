from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

from pydantic import field_validator
from typing_extensions import Self

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import Stringable
from darwin.future.data_objects.advanced_filters import GroupFilter, SubjectFilter
from darwin.future.data_objects.page import Page
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
    """
    Basic query filter with a name and a parameter
    Modifiers are for client side filtering only, and are not passed to the API
    Attributes
    ----------
    name: str
    param: str
    modifier: Optional[Modifiers]: Optional modifier to apply to the filter
    """

    name: str
    param: str
    modifier: Optional[Modifier] = None

    @field_validator("param")
    def validate_param(cls, v: Stringable) -> str:
        return str(v)

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

    def to_dict(self, ignore_modifier: bool = True) -> Dict[str, str]:
        d = {self.name: self.param}
        if self.modifier is not None and not ignore_modifier:
            d["modifier"] = self.modifier.value
        return d


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
        filter(name: str, param: str, modifier: Optional[Modifier] = None) -> Self:
            Adds a filter to the query object and returns a new query object.
        where(name: str, param: str, modifier: Optional[Modifier] = None) -> Self:
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
        self.results: dict[int, T] = {}
        self._changed_since_last: bool = False

    def filter(self, filter: QueryFilter) -> Self:
        return self + filter

    def __add__(self, filter: QueryFilter) -> Self:
        self._changed_since_last = True
        self.filters.append(filter)
        return self

    def __sub__(self, filter: QueryFilter) -> Self:
        self._changed_since_last = True
        return self.__class__(
            self.client,
            filters=[f for f in self.filters if f != filter],
            meta_params=self.meta_params,
        )

    def __iadd__(self, filter: QueryFilter) -> Self:
        self.filters.append(filter)
        self._changed_since_last = True
        return self

    def __isub__(self, filter: QueryFilter) -> Self:
        self.filters = [f for f in self.filters if f != filter]
        self._changed_since_last = True
        return self

    def __len__(self) -> int:
        if not self.results:
            self.results = {**self.results, **self._collect()}
        return len(self.results)

    def __iter__(self) -> Self:
        self.n = 0
        return self

    def __next__(self) -> T:
        if not self.results:
            self.collect()
        if self.n < len(self.results):
            result = self.results[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

    def __getitem__(self, index: int) -> T:
        if not self.results:
            self.results = {**self.results, **self._collect()}
        return self.results[index]

    def __setitem__(self, index: int, value: T) -> None:
        if not self.results:
            self.results = {**self.results, **self._collect()}
        self.results[index] = value

    def where(self, *args: object, **kwargs: str) -> Self:
        filters = QueryFilter._from_args(*args, **kwargs)
        for item in filters:
            self += item
        self._changed_since_last = True
        return self

    def collect(self, force: bool = False) -> List[T]:
        if force or self._changed_since_last:
            self.results = {}
        self.results = {**self.results, **self._collect()}
        self._changed_since_last = False
        return self._unwrap(self.results)

    def _unwrap(self, results: Dict[int, T]) -> List[T]:
        return list(results.values())

    @abstractmethod
    def _collect(self) -> Dict[int, T]:
        raise NotImplementedError("Not implemented")

    def collect_one(self) -> T:
        if not self.results:
            self.results = {**self.results, **self._collect()}
        if len(self.results) == 0:
            raise ResultsNotFound("No results found")
        if len(self.results) > 1:
            raise MoreThanOneResultFound("More than one result found")
        return self.results[0]

    def first(self) -> T:
        if not self.results:
            self.results = {**self.results, **self._collect()}
        if len(self.results) == 0:
            raise ResultsNotFound("No results found")

        return self.results[0]

    def _generic_execute_filter(self, objects: List[T], filter: QueryFilter) -> List[T]:
        return [
            m for m in objects if filter.filter_attr(getattr(m._element, filter.name))
        ]


class PaginatedQuery(Query[T]):
    def __init__(
        self,
        client: ClientCore,
        filters: List[QueryFilter] | None = None,
        meta_params: Param | None = None,
        page: Page | None = None,
    ):
        super().__init__(client, filters, meta_params)
        self._advanced_filters: GroupFilter | SubjectFilter | None = None
        self.page = page or Page()
        self.completed = False

    def collect(self, force: bool = False) -> List[T]:
        if force or self._changed_since_last:
            self.page = Page()
            self.completed = False
        if self.completed:
            return self._unwrap(self.results)
        new_results = self._collect()
        self.results = {**self.results, **new_results}
        if len(new_results) < self.page.size or len(new_results) == 0:
            self.completed = True
        else:
            self.page.increment()
        return self._unwrap(self.results)

    def collect_all(self, force: bool = False) -> List[T]:
        if force:
            self.page = Page()
            self.completed = False
            self.results = {}
        while not self.completed:
            self.collect()
        return self._unwrap(self.results)

    def __getitem__(self, index: int) -> T:
        if index not in self.results:
            temp_page = self.page
            self.page = self.page.get_required_page(index)
            self.collect()
            self.page = temp_page
        return super().__getitem__(index)

    def __next__(self) -> T:
        if not self.completed and self.n not in self.results:
            self.collect()
        if self.completed and self.n not in self.results:
            raise StopIteration
        result = self.results[self.n]
        self.n += 1
        return result

    def __len__(self) -> int:
        if not self.completed:
            self.collect_all()
        return len(self.results)
