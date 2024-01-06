import pytest
from pydantic import ValidationError

from darwin.future.data_objects.sorting import SortingMethods


def test_sorting_methods_all_fields_none():
    with pytest.raises(ValidationError):
        SortingMethods()


def test_sorting_methods_one_field_set():
    sorting = SortingMethods(accuracy="asc")
    assert sorting.accuracy == "asc"


def test_sorting_methods_multiple_fields_set():
    sorting = SortingMethods(accuracy="asc", byte_size="desc")
    assert sorting.accuracy == "asc"
    assert sorting.byte_size == "desc"


def test_sorting_methods_invalid_value():
    with pytest.raises(ValidationError):
        SortingMethods(accuracy="invalid")
