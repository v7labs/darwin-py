from __future__ import annotations

from math import floor
from typing import Optional

from pydantic import NonNegativeInt, PositiveInt

from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.pydantic_base import DefaultDarwin


def must_be_positive(v: int) -> int:
    if v is not None and v < 0:
        raise ValueError("Value must be positive")
    return v


class Page(DefaultDarwin):
    offset: Optional[NonNegativeInt] = None
    size: Optional[PositiveInt] = None
    count: Optional[NonNegativeInt] = None

    @classmethod
    def default(cls) -> Page:
        return Page(offset=0, size=500, count=0)

    def get_required_page(self, item_index: int) -> Page:
        """
        Get the page that contains the item at the specified index

        Args:
            item_index (int): The index of the item

        Returns:
            Page: The page that contains the item
        """
        assert self.size is not None
        required_offset = floor(item_index / self.size)
        return Page(offset=required_offset, size=self.size)

    def to_query_string(self) -> QueryString:
        """
        Generate a query string from the page object, some fields are not included if they are None,
        and certain fields are renamed. Outgoing and incoming query strings are different and require
        dropping certain fields

        Returns:
            QueryString: Outgoing query string
        """
        if self.offset is None and self.size is None:
            return QueryString({})
        elif self.offset is None:
            raise ValueError("Offset must be specified if size is specified")
        elif self.size is None:
            raise ValueError("Size must be specified if offset is specified")
        qs_dict = {"page[offset]": str(self.offset), "page[size]": str(self.size)}
        return QueryString(qs_dict)

    def increment(self) -> None:
        """
        Increment the page offset by the page size
        """
        if self.offset is None or self.size is None:
            self.offset = 0
            self.size = 500  # Default for darwin api
            return
        assert self.size is not None, "Size must be specified if offset is specified"
        self.offset += self.size
