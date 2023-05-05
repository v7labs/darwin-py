from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

from darwin.future.core.client import Client
from darwin.future.data_objects.darwin_meta import DefaultDarwin

T = TypeVar("T", bound=DefaultDarwin)


class QueryFilter(BaseModel):
    """Basic query filter with a name and a parameter

    Attributes
    ----------
    name: str
    param: str
    """

    name: str
    param: str


class Query(Generic[T], ABC):
    """Basic Query object with methods to manage filters
    Methods:
        filter: adds a filter to the query object, returns a new query object
    """

    def __init__(self, filters: Optional[List[QueryFilter]] = None):
        self.filters = filters

    def filter(self, filter: QueryFilter) -> Query:
        return self + filter

    def __add__(self, filter: QueryFilter) -> Query:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            self.filters = []
        return self.__class__([*self.filters, filter])

    def __sub__(self, filter: QueryFilter) -> Query:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            return self
        return self.__class__([f for f in self.filters if f != filter])

    def __iadd__(self, filter: QueryFilter) -> Query:
        assert filter is not None
        assert isinstance(filter, QueryFilter)
        if self.filters is None:
            self.filters = [filter]
            return self
        self.filters.append(filter)
        return self

    def __isub__(self, filter: QueryFilter) -> Query:
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

    def __iter__(self) -> Query:
        self.n = 0
        return self

    def __next__(self) -> QueryFilter:
        if self.filters is None:
            self.filters = []
        if self.n < len(self.filters):
            result = self.filters[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration

    @abstractmethod
    def collect(self, client: Client) -> List[T]:
        raise NotImplementedError("Not implemented")


class ServerSideQuery(Query):
    """Server side query object
    TODO: add server specific methods and paramenters
    """


class ClientSideQuery(Query):
    """Client side query object
    TODO: add client side specific methods and parameters
    """

    def __init__(self, model: DefaultDarwin, filters: Optional[List[QueryFilter]] = None):
        super().__init__(filters)
        self.model = model
