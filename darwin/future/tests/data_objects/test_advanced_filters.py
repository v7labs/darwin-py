from datetime import datetime, timedelta
from typing import List, Tuple, get_args

import pytest
from pydantic import ValidationError

from darwin.future.data_objects import advanced_filters as AF

FileTypesParameters: List[Tuple[AF.AcceptedFileTypes]] = list(
    get_args(AF.AcceptedFileTypes)
)

IssueTypes: List[Tuple[AF.IssueType]] = list(get_args(AF.IssueType))
ProcessingStatusTypes: List[Tuple[AF.ProcessingStatusType]] = list(
    get_args(AF.ProcessingStatusType)
)
WorkflowStatusTypes: List[Tuple[AF.WorkflowStatusType]] = list(
    get_args(AF.WorkflowStatusType)
)


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
    AF.GroupFilter(filters=[AF.AnnotationClass.all_of([1, 2]), AF.Assignee.any_of([1])])


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
        matcher=AF.AllOf[int](values=[1, 2, 3])
    )
    assert AF.AnnotationClass.none_of([1, 2, 3]) == AF.AnnotationClass(
        matcher=AF.NoneOf[int](values=[1, 2, 3])
    )
    assert AF.AnnotationClass.any_of([1, 2, 3]) == AF.AnnotationClass(
        matcher=AF.AnyOf[int](values=[1, 2, 3])
    )


def test_assignee() -> None:
    assert AF.Assignee.all_of([1, 2, 3]) == AF.Assignee(
        matcher=AF.AllOf[int](values=[1, 2, 3])
    )
    assert AF.Assignee.none_of([1, 2, 3]) == AF.Assignee(
        matcher=AF.NoneOf[int](values=[1, 2, 3])
    )
    assert AF.Assignee.any_of([1, 2, 3]) == AF.Assignee(
        matcher=AF.AnyOf[int](values=[1, 2, 3])
    )


def test_created_at() -> None:
    after = datetime.now()
    before = after - timedelta(days=1)
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
        matcher=AF.NoneOf[int](values=[1, 2, 3])
    )
    assert AF.CurrentAssignee.any_of([1, 2, 3]) == AF.CurrentAssignee(
        matcher=AF.AnyOf[int](values=[1, 2, 3])
    )


@pytest.mark.parametrize("file_type", FileTypesParameters)
def test_file_type(file_type: AF.AcceptedFileTypes) -> None:
    assert AF.FileType.any_of([file_type]) == AF.FileType(
        matcher=AF.AnyOf[AF.AcceptedFileTypes](values=[file_type])
    )
    assert AF.FileType.none_of([file_type]) == AF.FileType(
        matcher=AF.NoneOf[AF.AcceptedFileTypes](values=[file_type])
    )
    assert AF.FileType.any_of([file_type]) == AF.FileType(
        matcher=AF.AnyOf[AF.AcceptedFileTypes](values=[file_type])
    )


def test_file_type_breaks() -> None:
    with pytest.raises(ValidationError):
        AF.FileType.any_of(["not a valid filetype"])  # type: ignore


def test_folder_path() -> None:
    assert AF.FolderPath.any_of(["test"]) == AF.FolderPath(
        matcher=AF.AnyOf[str](values=["test"])
    )
    assert AF.FolderPath.none_of(["test"]) == AF.FolderPath(
        matcher=AF.NoneOf[str](values=["test"])
    )
    assert AF.FolderPath.any_of(["test"]) == AF.FolderPath(
        matcher=AF.AnyOf[str](values=["test"])
    )


def test_id() -> None:
    assert AF.ID.any_of(["test"]) == AF.ID(matcher=AF.AnyOf[str](values=["test"]))
    assert AF.ID.none_of(["test"]) == AF.ID(matcher=AF.NoneOf[str](values=["test"]))


@pytest.mark.parametrize("issue_type", IssueTypes)
def test_issue(issue_type: AF.IssueType) -> None:
    assert AF.Issue.any_of([issue_type]) == AF.Issue(
        matcher=AF.AnyOf[AF.IssueType](values=[issue_type])
    )
    assert AF.Issue.none_of([issue_type]) == AF.Issue(
        matcher=AF.NoneOf[AF.IssueType](values=[issue_type])
    )


def test_issue_breaks() -> None:
    with pytest.raises(ValidationError):
        AF.Issue.any_of(["not a valid issue type"])  # type: ignore


def test_item_name() -> None:
    assert AF.ItemName.any_of(["test"]) == AF.ItemName(
        matcher=AF.AnyOf[str](values=["test"])
    )
    assert AF.ItemName.none_of(["test"]) == AF.ItemName(
        matcher=AF.NoneOf[str](values=["test"])
    )
    assert AF.ItemName.prefix("test") == AF.ItemName(matcher=AF.Prefix(value="test"))
    assert AF.ItemName.suffix("test") == AF.ItemName(matcher=AF.Suffix(value="test"))
    assert AF.ItemName.contains("test") == AF.ItemName(
        matcher=AF.Contains(value="test")
    )
    assert AF.ItemName.not_contains("test") == AF.ItemName(
        matcher=AF.NotContains(value="test")
    )


@pytest.mark.parametrize("processing_status", ProcessingStatusTypes)
def test_processing_status(processing_status: AF.ProcessingStatusType) -> None:
    assert AF.ProcessingStatus.any_of([processing_status]) == AF.ProcessingStatus(
        matcher=AF.AnyOf[AF.ProcessingStatusType](values=[processing_status])
    )
    assert AF.ProcessingStatus.none_of([processing_status]) == AF.ProcessingStatus(
        matcher=AF.NoneOf[AF.ProcessingStatusType](values=[processing_status])
    )


def test_processing_status_breaks() -> None:
    with pytest.raises(ValidationError):
        AF.ProcessingStatus.any_of(["not a valid processing status"])  # type: ignore


def test_updated_at() -> None:
    after = datetime.now()
    before = after - timedelta(days=1)
    assert AF.UpdatedAt.between(before, after) == AF.UpdatedAt(
        matcher=AF.DateRange(start=before, end=after)
    )
    assert AF.UpdatedAt.after(before) == AF.UpdatedAt(
        matcher=AF.DateRange(start=before)
    )
    assert AF.UpdatedAt.before(after) == AF.UpdatedAt(matcher=AF.DateRange(end=after))

    # Check raises if time is not in order
    with pytest.raises(ValidationError):
        AF.UpdatedAt.between(after, before)


@pytest.mark.parametrize("workflow_status", WorkflowStatusTypes)
def test_workflow_status(workflow_status: AF.WorkflowStatusType) -> None:
    assert AF.WorkflowStatus.any_of([workflow_status]) == AF.WorkflowStatus(
        matcher=AF.AnyOf[AF.WorkflowStatusType](values=[workflow_status])
    )
    assert AF.WorkflowStatus.none_of([workflow_status]) == AF.WorkflowStatus(
        matcher=AF.NoneOf[AF.WorkflowStatusType](values=[workflow_status])
    )


def test_workflow_status_breaks() -> None:
    with pytest.raises(ValidationError):
        AF.WorkflowStatus.any_of(["not a valid workflow status"])  # type: ignore


def test_workflow_stage() -> None:
    assert AF.WorkflowStage.any_of(["test"]) == AF.WorkflowStage(
        matcher=AF.AnyOf[str](values=["test"])
    )
    assert AF.WorkflowStage.none_of(["test"]) == AF.WorkflowStage(
        matcher=AF.NoneOf[str](values=["test"])
    )


def test_GF_validators() -> None:
    with pytest.raises(ValidationError):
        AF.GroupFilter(filters=[])  # needs at least two filters
        AF.GroupFilter(filters=[AF.AnnotationClass.all_of([1, 2])])
