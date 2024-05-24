import pytest

from darwin.item_sorter import ItemSorter, SortDirection


class TestItemSorter:
    def test_works_when_sort_is_complete_and_valid(self):
        sort = "updated_at:asc"

        actual: ItemSorter = ItemSorter.parse(sort)

        assert actual.field == "updated_at"
        assert actual.direction == SortDirection.ASCENDING

    def test_works_when_sort_is_partial_and_valid(self):
        sort = "updated_at"

        actual: ItemSorter = ItemSorter.parse(sort)

        assert actual.field == "updated_at"
        assert actual.direction == SortDirection.ASCENDING

    def test_raises_when_sort_has_invalid_format(self):
        sort = "updated_at:asc:desc:"

        with pytest.raises(ValueError) as error:
            ItemSorter.parse(sort)

        assert (
            f"Invalid sort parameter '{sort}'. Correct format is 'field:direction' where 'direction' is optional and defaults to 'asc', i.e. 'updated_at:asc' or just 'updated_at'."
            in str(error.value)
        )

    def test_raises_when_sort_has_invalid_field(self):
        field = "asdf"
        sort = f"{field}:asc"

        with pytest.raises(ValueError) as error:
            ItemSorter.parse(sort)

        assert (
            f"Invalid sort parameter '{field}', available sort fields: 'inserted_at', 'updated_at', 'file_size', 'filename', 'priority'."
            in str(error.value)
        )


class TestSortDirection:
    def test_returns_asc_enum_when_given_asc_direction(self):
        short_direction = "asc"
        long_direction = "ascending"

        assert SortDirection.parse(short_direction) == SortDirection.ASCENDING
        assert SortDirection.parse(long_direction) == SortDirection.ASCENDING

    def test_returns_desc_enum_when_given_desc_direction(self):
        short_direction = "desc"
        long_direction = "descending"

        assert SortDirection.parse(short_direction) == SortDirection.DESCENDING
        assert SortDirection.parse(long_direction) == SortDirection.DESCENDING

    def test_raises_when_direction_is_invalid(self):
        direction = "bad_direction"

        with pytest.raises(ValueError) as error:
            SortDirection.parse(direction)

        assert (
            f"Invalid direction '{direction}', use 'asc' or 'ascending', 'desc' or 'descending'."
            in str(error.value)
        )
