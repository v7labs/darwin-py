from enum import Enum
from typing import Union


class SortDirection(Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

    @classmethod
    def parse(cls, direction: str):
        normalized_direction = direction.lower()

        if cls._is_ascending(normalized_direction):
            return cls.ASCENDING
        if cls._is_descending(normalized_direction):
            return cls.DESCENDING

        raise ValueError(f"Invalid direction '{direction}', use 'asc' or 'ascending', 'desc' or 'descending'.")

    @staticmethod
    def _is_ascending(direction: str) -> bool:
        return direction == "asc" or direction == "ascending"

    @staticmethod
    def _is_descending(direction: str) -> bool:
        return direction == "desc" or direction == "descending"


class ItemSorter:
    def __init__(self, field: str, direction: SortDirection):
        self.field = field
        self.direction = direction

    @classmethod
    def parse(cls, sort: Union[str, "ItemSorter"]) -> "ItemSorter":
        if isinstance(sort, ItemSorter):
            return sort

        if not cls._has_valid_format(sort):
            raise ValueError(
                f"Invalid sort parameter '{sort}'. Correct format is 'field:direction' where 'direction' is optional and defaults to 'asc', i.e. 'updated_at:asc' or just 'updated_at'."
            )

        if not cls._has_direction(sort):
            field = sort
            direction = "asc"
        else:
            field, direction = sort.split(":")

        if not cls._has_valid_field(field):
            raise ValueError(
                f"Invalid sort parameter '{field}', available sort fields: 'inserted_at', 'updated_at', 'file_size', 'filename', 'priority'."
            )

        return cls(field=field, direction=SortDirection.parse(direction))

    @staticmethod
    def _has_direction(sort: str) -> bool:
        return ":" in sort

    @staticmethod
    def _has_valid_format(sort_by: str) -> bool:
        return len(sort_by.split(":")) in [1, 2]

    @staticmethod
    def _has_valid_field(sort: str) -> bool:
        return sort in ["inserted_at", "updated_at", "file_size", "filename", "priority"]

    def __str__(self):
        return f"{self.field}:{self.direction.value}"
