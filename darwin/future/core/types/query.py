from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from darwin.future.data_objects.darwin import Team


class Query(ABC):
    def __init__(self, team: Team, filters: Dict = {}):
        self.team = team
        self.filters = filters

    def where(self, **kwargs: str) -> Query:
        return Query(self.team, {**self.filters, **kwargs})
