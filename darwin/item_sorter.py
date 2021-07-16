from enum import Enum
from typing import Optional


class SortDirection(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

    @classmethod
    def parse(cls, direction):
        direction = direction.lower()
        if direction == "asc" or direction == "ascending":
            return cls.ASCENDING
        if direction == "desc" or direction == "descending":
            return cls.DESCENDING
        raise ValueError(f"Invalid direction '{direction}', use 'asc' or 'desc'")

class ItemSorter:
    def __init__(self, field: str, direction: SortDirection):
        self.field = field
        self.direction = direction

    @classmethod
    def parse(cls, sort_order: str):
        if len(sort_order.split(":")) > 2:
            raise ValueError(f"Invalid sort '{sort_order}'")

        if ":" not in sort_order:
            field = sort_order
            direction = "asc"
        else: 
            field, direction = sort_order.split(":")

        if not _has_valid_attribute(field):
            raise ValueError(f"Invalid sort field `{field}`, use one of inserted_at, updated_at, file_size, filename, priority")
        
        return cls(field=field, direction=SortDirection.parse(direction))

    def __str__(self):
       return f"{self.field}:{self.direction.value}"

def _has_valid_attribute(sort: str) -> bool:
    return sort in ["inserted_at", "updated_at", "file_size", "filename", "priority"]
