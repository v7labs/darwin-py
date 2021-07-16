import pytest

from darwin.item_sorter import ItemSorter, SortDirection


def describe_item_sorter():
    def describe_parse():
        def works_when_sort_is_complete_and_valid():
            sort = "updated_at:asc"

            actual: ItemSorter = ItemSorter.parse(sort)

            assert actual.field == "updated_at"
            assert actual.direction == SortDirection.ASCENDING

        def works_when_sort_is_partial_and_valid():
            sort = "updated_at"

            actual: ItemSorter = ItemSorter.parse(sort)

            assert actual.field == "updated_at"
            assert actual.direction == SortDirection.ASCENDING

        def raises_when_sort_has_invalid_format():
            sort = "updated_at:asc:desc:"

            with pytest.raises(ValueError) as error:
                ItemSorter.parse(sort)

            assert (
                f"Invalid sort parameter '{sort}'. Correct format is 'field:direction' where 'direction' is optional and defaults to 'asc', i.e. 'updated_at:asc' or just 'updated_at'."
                in str(error.value)
            )

        def raises_when_sort_has_invalid_field():
            field = "asdf"
            sort = f"{field}:asc"

            with pytest.raises(ValueError) as error:
                ItemSorter.parse(sort)

            assert (
                f"Invalid sort parameter '{field}', available sort fields: 'inserted_at', 'updated_at', 'file_size', 'filename', 'priority'."
                in str(error.value)
            )


def describe_sort_direction():
    def describe_parse():
        def returns_asc_enum_when_given_asc_direction():
            short_direction = "asc"
            long_direction = "ascending"

            assert SortDirection.parse(short_direction) == SortDirection.ASCENDING
            assert SortDirection.parse(long_direction) == SortDirection.ASCENDING

        def returns_desc_enum_when_given_desc_direction():
            short_direction = "desc"
            long_direction = "descending"

            assert SortDirection.parse(short_direction) == SortDirection.DESCENDING
            assert SortDirection.parse(long_direction) == SortDirection.DESCENDING

        def raises_when_direction_is_invalid():
            direction = "bad_direction"

            with pytest.raises(ValueError) as error:
                SortDirection.parse(direction)

            assert f"Invalid direction '{direction}', use 'asc' or 'ascending', 'desc' or 'descending'." in str(
                error.value
            )
