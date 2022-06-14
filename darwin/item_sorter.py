from typing import Union

from darwin.doc_enum import DocEnum


class SortDirection(DocEnum):
    """
    The sorting direction of items.
    """

    ASCENDING = "asc", "Ascending sort order."
    DESCENDING = "desc", "Descending sort order."

    @classmethod
    def parse(cls, direction: str) -> "SortDirection":
        """
        Parses the given direction and returns the corresponding sort Enum.

        Parameters
        ----------
        direction: str
            The direction of the sorting order. Can be 'asc' or 'ascending', 'desc' or 'descending'.

        Returns
        -------
        SortDirection
            The Enum representing a sorting direction.

        Raises
        ------
        ValueError
            If the ``direction`` given is invalid.
        """
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
    """
    Represents sorting for list of items.

    Parameters
    ----------
    field : str
        The name of the field to be sorted.
    direction : SortDirection
        The direction of the sort.
    """

    def __init__(self, field: str, direction: SortDirection):
        self.field = field
        self.direction = direction

    @classmethod
    def parse(cls, sort: Union[str, "ItemSorter"]) -> "ItemSorter":
        """
        Parses the sorting given into an ItemSorter, capable of being used by Darwin.

        Parameters
        ----------
        sort : Union[str, ItemSorter]
            The sort order. If it is a ``str``, it will be parsed, otherwise it returns the
            ``ItemSorter``.

        Returns
        -------
        ItemSorter
            A parsed ``ItemSorter`` representing a sorting direction.

        Raises
        ------
        ValueError
            If the given sort parameter is invalid.
        """
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
