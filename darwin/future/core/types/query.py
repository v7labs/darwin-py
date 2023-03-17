from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel

from darwin.future.data_objects.darwin_meta import Team


class QueryFilter(BaseModel):
    name: str
    param: str


class Result(BaseModel):
    pass


class Cursor(ABC):
    @abstractmethod
    def __iter__(self) -> Result:
        pass


class Query(ABC):
    def __init__(self, team: Team, filters: Optional[List[QueryFilter]] = None):
        self.team = team
        self.filters = filters

    @abstractmethod
    def filter(self, filter: QueryFilter) -> Query:
        pass

    @abstractmethod
    def execute(self) -> dict:
        pass


class ServerSideQuery(Query):
    def filter(self, filter: QueryFilter) -> ServerSideQuery:
        if self.filters is None:
            self.filters = []

        return ServerSideQuery(self.team, [*self.filters, filter])

    def execute(self) -> dict:
        return {}
