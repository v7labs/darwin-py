from datetime import datetime, timedelta
from typing import List, Tuple, get_args

import pytest
from pydantic import ValidationError

from darwin.future.data_objects import advanced_filters as AF

FileTypesParameters: List[Tuple[AF.AcceptedFileTypes]] = [
    (x) for x in list(get_args(AF.AcceptedFileTypes))
]


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
        AF.AnyOf[int](values=[])  # needs at least one value

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


# test instantiatiors and factories
def test_annotation_class() -> None:
    assert AF.AnnotationClass.all_of([1, 2, 3]) == AF.AnnotationClass(
        matcher=AF.AllOf(values=[1, 2, 3])
    )
    assert AF.AnnotationClass.none_of([1, 2, 3]) == AF.AnnotationClass(
        matcher=AF.NoneOf(values=[1, 2, 3])
    )
    assert AF.AnnotationClass.any_of([1, 2, 3]) == AF.AnnotationClass(
        matcher=AF.AnyOf(values=[1, 2, 3])
    )


def test_assignee() -> None:
    assert AF.Assignee.all_of([1, 2, 3]) == AF.Assignee(
        matcher=AF.AllOf(values=[1, 2, 3])
    )
    assert AF.Assignee.none_of([1, 2, 3]) == AF.Assignee(
        matcher=AF.NoneOf(values=[1, 2, 3])
    )
    assert AF.Assignee.any_of([1, 2, 3]) == AF.Assignee(
        matcher=AF.AnyOf(values=[1, 2, 3])
    )


def test_created_at() -> None:
    before = datetime.now()
    after = datetime.now()
    assert AF.CreatedAt.between(before, after) == AF.CreatedAt(
        matcher=AF.DateRange(start=before, end=after)
    )
    assert AF.CreatedAt.after(before) == AF.CreatedAt(
        matcher=AF.DateRange(start=before)
    )
    assert AF.CreatedAt.before(after) == AF.CreatedAt(matcher=AF.DateRange(end=after))

    # Check raises if time is not in order
    with pytest.raises(ValidationError):
        AF.CreatedAt.between(after, before)


def test_current_assignee() -> None:
    assert AF.CurrentAssignee.none_of([1, 2, 3]) == AF.CurrentAssignee(
        matcher=AF.NoneOf(values=[1, 2, 3])
    )
    assert AF.CurrentAssignee.any_of([1, 2, 3]) == AF.CurrentAssignee(
        matcher=AF.AnyOf(values=[1, 2, 3])
    )


@pytest.mark.parametrize("file_type", FileTypesParameters)
def test_file_type(file_type: AF.AcceptedFileTypes) -> None:
    assert AF.FileType.any_of([file_type]) == AF.FileType(
        matcher=AF.AnyOf(values=[file_type])
    )
    assert AF.FileType.none_of([file_type]) == AF.FileType(
        matcher=AF.NoneOf(values=[file_type])
    )
    assert AF.FileType.any_of([file_type]) == AF.FileType(
        matcher=AF.AnyOf(values=[file_type])
    )
