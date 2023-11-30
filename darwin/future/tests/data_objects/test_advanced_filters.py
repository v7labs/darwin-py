from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from darwin.future.data_objects import advanced_filters as AF


def test_date_validator() -> None:
    with pytest.raises(ValidationError):
        AF.DateRange()  # needs at least one date

    with pytest.raises(ValidationError):
        # start date must be before end date
        start = datetime.now()
        end = start - timedelta(days=1)
        AF.DateRange(start=start, end=end)

    # Test instantiates
    AF.DateRange(start=datetime.now())
    AF.DateRange(end=datetime.now())
    AF.DateRange(start=datetime.now(), end=datetime.now())


def test_any_of_validator() -> None:
    with pytest.raises(ValidationError):
        AF.AnyOf[int](values=[1])  # needs at least two values

    # Test instantiates
    AF.AnyOf[int](values=[1, 2])


def test_none_of_validator() -> None:
    with pytest.raises(ValidationError):
        AF.NoneOf[int](values=[])  # needs at least one value

    # Test instantiates
    AF.NoneOf[int](values=[1])


def test_all_of_validator() -> None:
    with pytest.raises(ValidationError):
        AF.AllOf[int](values=[])  # needs at least one value

    # Test instantiates
    AF.AllOf[int](values=[1])


def test_group_validator() -> None:
    with pytest.raises(ValidationError):
        AF.GroupFilter(filters=[])  # needs at least one filter

    # Test instantiates
    AF.GroupFilter(filters=[AF.AnnotationClass.all_of([1, 2])])


def test_bitwise_syntax() -> None:
    # test 'and'
    sf = AF.AnnotationClass.all_of([1, 2, 3])
    gf_and = AF.GroupFilter(conjunction="and", filters=[sf, sf])
    assert gf_and == sf & sf
    assert gf_and & sf == sf & sf & sf
    assert gf_and | sf == AF.GroupFilter(conjunction="or", filters=[gf_and, sf])

    # test 'or'
    gf_or = AF.GroupFilter(conjunction="or", filters=[sf, sf])
    assert gf_or == sf | sf
    assert gf_or | sf == sf | sf | sf
    assert gf_or & sf == AF.GroupFilter(conjunction="and", filters=[gf_or, sf])

    # test mixed 'and' and 'or'
    assert gf_and & gf_or == AF.GroupFilter(conjunction="and", filters=[gf_and, gf_or])
    assert gf_or & gf_and == AF.GroupFilter(conjunction="and", filters=[gf_or, gf_and])
    assert gf_and | gf_or == AF.GroupFilter(conjunction="or", filters=[gf_and, gf_or])
    assert gf_or | gf_and == AF.GroupFilter(conjunction="or", filters=[gf_or, gf_and])
