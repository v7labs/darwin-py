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

    AF.DateRange(start=datetime.now())
    AF.DateRange(end=datetime.now())
    AF.DateRange(start=datetime.now(), end=datetime.now())


def test_any_of_validator() -> None:
    with pytest.raises(ValidationError):
        AF.AnyOf[int](values=[1])  # needs at least two values
    AF.AnyOf[int](values=[1, 2])


def test_none_of_validator() -> None:
    with pytest.raises(ValidationError):
        AF.NoneOf[int](values=[])  # needs at least one value
    AF.NoneOf[int](values=[1])


def test_all_of_validator() -> None:
    with pytest.raises(ValidationError):
        AF.AllOf[int](values=[])  # needs at least one value
    AF.AllOf[int](values=[1])


def test_group_validator() -> None:
    with pytest.raises(ValidationError):
        AF.GroupFilter(filters=[])  # needs at least one filter
    AF.GroupFilter(filters=[AF.AnnotationClass.all_of([1, 2])])
