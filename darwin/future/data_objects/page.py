from __future__ import annotations

from math import floor

from pydantic import NonNegativeInt, PositiveInt

from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.pydantic_base import DefaultDarwin


def must_be_positive(v: int) -> int:
    if v is not None and v < 0:
        raise ValueError("Value must be positive")
    return v


class Page(DefaultDarwin):
    offset: NonNegativeInt = 0
    size: PositiveInt = 500

    def get_required_page(self, item_index: int) -> Page:
        """
        Get the page that contains the item at the specified index

        Args:
            item_index (int): The index of the item

        Returns:
            Page: The page that contains the item
        """
        assert self.size is not None
        required_offset = floor(item_index / self.size) * self.size
        return Page(offset=required_offset, size=self.size)

    def to_query_string(self) -> QueryString:
        """
        Generate a query string from the page object, some fields are not included if they are None,
        and certain fields are renamed. Outgoing and incoming query strings are different and require
        dropping certain fields

        Returns:
            QueryString: Outgoing query string
        """
        qs_dict = {"page[offset]": str(self.offset), "page[size]": str(self.size)}
        return QueryString(qs_dict)

    def increment(self) -> None:
        """
        Increment the page offset by the page size
        """
        self.offset += self.size
