from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from darwin.future.data_objects.darwin_meta import Team


class Filter(ABC):
    pass


class Query(ABC):
    def __init__(self, team: Team, filters: Optional[Filter] = None):
        self.team = team
        self.filters = filters

    def where(self, **kwargs: str) -> Query:
        return Query(self.team, {**self.filters, **kwargs})
