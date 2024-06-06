from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Literal, Optional, TypeVar, Union

from pydantic import BaseModel, SerializeAsAny, field_validator, model_validator

T = TypeVar("T")

AcceptedFileTypes = Literal["image", "video", "pdf", "dicom"]
IssueType = Literal["comment"]
ProcessingStatusType = Literal[
    "cancelled", "error", "uploading", "uploading_confirmed", "processing", "complete"
]
WorkflowStatusType = Literal["new", "annotate", "review", "complete"]


def validate_at_least_one(value: list[T]) -> list[T]:
    if len(value) < 1:
        raise ValueError("Must provide at least one value.")
    return list(set(value))


class BaseMatcher(BaseModel):
    name: str


class AnyOf(BaseMatcher, Generic[T]):
    name: Literal["any_of"] = "any_of"
    values: List[T]

    _normalize_values = field_validator("values")(validate_at_least_one)


class AllOf(BaseMatcher, Generic[T]):
    name: Literal["all_of"] = "all_of"
    values: List[T]

    _normalize_values = field_validator("values")(validate_at_least_one)


class NoneOf(BaseMatcher, Generic[T]):
    name: Literal["none_of"] = "none_of"
    values: List[T]

    _normalize_values = field_validator("values")(validate_at_least_one)


class Equals(BaseMatcher, Generic[T]):
    name: Literal["equals"] = "equals"
    value: T


class DateRange(BaseMatcher):
    name: Literal["date_range"] = "date_range"
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    @model_validator(mode="before")
    def validate_date_range(cls, values: dict) -> dict:
        if not values.get("start") and not values.get("end"):
            raise ValueError("At least one of 'start' or 'end' must be provided.")
        if values.get("start") and values.get("end"):
            if values["start"] > values["end"]:
                raise ValueError("'start' must be before 'end'.")
        return values


class Prefix(BaseMatcher):
    name: Literal["prefix"] = "prefix"
    value: str


class Suffix(BaseMatcher):
    name: Literal["suffix"] = "suffix"
    value: str


class Contains(BaseMatcher):
    name: Literal["contains"] = "contains"
    value: str


class NotContains(BaseMatcher):
    name: Literal["not_contains"] = "not_contains"
    value: str


class SubjectFilter(BaseModel):
    subject: str
    matcher: SerializeAsAny[BaseMatcher]

    def __and__(self, other: SubjectFilter | GroupFilter) -> GroupFilter:
        if isinstance(other, GroupFilter):
            return GroupFilter(conjunction="and", filters=[self, other])
        return GroupFilter(conjunction="and", filters=[self, other])

    def __or__(self, other: SubjectFilter | GroupFilter) -> GroupFilter:
        if isinstance(other, GroupFilter):
            return GroupFilter(conjunction="or", filters=[self, other])
        return GroupFilter(conjunction="or", filters=[self, other])


# Subject Filters
class AnnotationClass(SubjectFilter):
    subject: Literal["annotation_class"] = "annotation_class"
    matcher: Union[AnyOf[int], AllOf[int], NoneOf[int]]

    @classmethod
    def any_of(cls, values: list[int]) -> AnnotationClass:
        return AnnotationClass(
            subject="annotation_class", matcher=AnyOf[int](values=values)
        )

    @classmethod
    def all_of(cls, values: list[int]) -> AnnotationClass:
        return AnnotationClass(
            subject="annotation_class", matcher=AllOf[int](values=values)
        )

    @classmethod
    def none_of(cls, values: list[int]) -> AnnotationClass:
        return AnnotationClass(
            subject="annotation_class", matcher=NoneOf[int](values=values)
        )


class Archived(SubjectFilter):
    subject: Literal["archived"] = "archived"
    matcher: Equals[bool]

    @classmethod
    def equals(cls, value: bool) -> Archived:
        return Archived(subject="archived", matcher=Equals(value=value))


class Assignee(SubjectFilter):
    subject: Literal["assignee"] = "assignee"
    matcher: Union[AnyOf[int], AllOf[int], NoneOf[int]]

    @classmethod
    def any_of(cls, values: list[int]) -> Assignee:
        return Assignee(subject="assignee", matcher=AnyOf[int](values=values))

    @classmethod
    def all_of(cls, values: list[int]) -> Assignee:
        return Assignee(subject="assignee", matcher=AllOf[int](values=values))

    @classmethod
    def none_of(cls, values: list[int]) -> Assignee:
        return Assignee(subject="assignee", matcher=NoneOf[int](values=values))


class CreatedAt(SubjectFilter):
    subject: Literal["created_at"] = "created_at"
    matcher: DateRange

    @classmethod
    def between(cls, start: datetime, end: datetime) -> CreatedAt:
        return CreatedAt(subject="created_at", matcher=DateRange(start=start, end=end))

    @classmethod
    def before(cls, end: datetime) -> CreatedAt:
        return CreatedAt(subject="created_at", matcher=DateRange(end=end))

    @classmethod
    def after(cls, start: datetime) -> CreatedAt:
        return CreatedAt(subject="created_at", matcher=DateRange(start=start))


class CurrentAssignee(SubjectFilter):
    subject: Literal["current_assignee"] = "current_assignee"
    matcher: Union[AnyOf[int], NoneOf[int]]

    @classmethod
    def any_of(cls, values: list[int]) -> CurrentAssignee:
        return CurrentAssignee(
            subject="current_assignee", matcher=AnyOf[int](values=values)
        )

    @classmethod
    def none_of(cls, values: list[int]) -> CurrentAssignee:
        return CurrentAssignee(
            subject="current_assignee", matcher=NoneOf[int](values=values)
        )


class FileType(SubjectFilter):
    subject: Literal["file_type"] = "file_type"
    matcher: Union[
        AnyOf[AcceptedFileTypes], AllOf[AcceptedFileTypes], NoneOf[AcceptedFileTypes]
    ]

    @classmethod
    def any_of(cls, values: list[AcceptedFileTypes]) -> FileType:
        return FileType(
            subject="file_type", matcher=AnyOf[AcceptedFileTypes](values=values)
        )

    @classmethod
    def all_of(cls, values: list[AcceptedFileTypes]) -> FileType:
        return FileType(
            subject="file_type", matcher=AllOf[AcceptedFileTypes](values=values)
        )

    @classmethod
    def none_of(cls, values: list[AcceptedFileTypes]) -> FileType:
        return FileType(
            subject="file_type", matcher=NoneOf[AcceptedFileTypes](values=values)
        )


class FolderPath(SubjectFilter):
    subject: Literal["folder_path"] = "folder_path"
    matcher: Union[AnyOf[str], NoneOf[str], Prefix, Suffix]

    @classmethod
    def any_of(cls, values: list[str]) -> FolderPath:
        return FolderPath(subject="folder_path", matcher=AnyOf[str](values=values))

    @classmethod
    def none_of(cls, values: list[str]) -> FolderPath:
        return FolderPath(subject="folder_path", matcher=NoneOf[str](values=values))

    @classmethod
    def prefix(cls, value: str) -> FolderPath:
        return FolderPath(subject="folder_path", matcher=Prefix[str](value=value))

    @classmethod
    def suffix(cls, value: str) -> FolderPath:
        return FolderPath(subject="folder_path", matcher=Suffix[str](value=value))


class ID(SubjectFilter):
    subject: Literal["id"] = "id"
    matcher: Union[AnyOf[str], NoneOf[str]]

    @classmethod
    def any_of(cls, values: list[str]) -> ID:
        return ID(subject="id", matcher=AnyOf[str](values=values))

    @classmethod
    def none_of(cls, values: list[str]) -> ID:
        return ID(subject="id", matcher=NoneOf[str](values=values))


class Issue(SubjectFilter):
    subject: Literal["issue"] = "issue"
    matcher: Union[AnyOf[IssueType], NoneOf[IssueType]]

    @classmethod
    def any_of(cls, values: list[IssueType]) -> Issue:
        return Issue(subject="issue", matcher=AnyOf[IssueType](values=values))

    @classmethod
    def none_of(cls, values: list[IssueType]) -> Issue:
        return Issue(subject="issue", matcher=NoneOf[IssueType](values=values))


class ItemName(SubjectFilter):
    subject: Literal["item_name"] = "item_name"
    matcher: Union[AnyOf[str], NoneOf[str], Prefix, Suffix, Contains, NotContains]

    @classmethod
    def any_of(cls, values: list[str]) -> ItemName:
        return ItemName(subject="item_name", matcher=AnyOf[str](values=values))

    @classmethod
    def none_of(cls, values: list[str]) -> ItemName:
        return ItemName(subject="item_name", matcher=NoneOf[str](values=values))

    @classmethod
    def prefix(cls, value: str) -> ItemName:
        return ItemName(subject="item_name", matcher=Prefix(value=value))

    @classmethod
    def suffix(cls, value: str) -> ItemName:
        return ItemName(subject="item_name", matcher=Suffix(value=value))

    @classmethod
    def contains(cls, value: str) -> ItemName:
        return ItemName(subject="item_name", matcher=Contains(value=value))

    @classmethod
    def not_contains(cls, value: str) -> ItemName:
        return ItemName(subject="item_name", matcher=NotContains(value=value))


class ProcessingStatus(SubjectFilter):
    subject: Literal["processing_status"] = "processing_status"
    matcher: Union[AnyOf[ProcessingStatusType], NoneOf[ProcessingStatusType]]

    @classmethod
    def any_of(cls, values: list[ProcessingStatusType]) -> ProcessingStatus:
        return ProcessingStatus(
            subject="processing_status",
            matcher=AnyOf[ProcessingStatusType](values=values),
        )

    @classmethod
    def none_of(cls, values: list[ProcessingStatusType]) -> ProcessingStatus:
        return ProcessingStatus(
            subject="processing_status",
            matcher=NoneOf[ProcessingStatusType](values=values),
        )


class ClassProperty(SubjectFilter):
    subject: Literal["class_property"] = "class_property"
    matcher: Union[AnyOf[str], AllOf[str], NoneOf[str]]

    @classmethod
    def any_of(cls, values: list[str]) -> ClassProperty:
        return ClassProperty(
            subject="class_property", matcher=AnyOf[str](values=values)
        )

    @classmethod
    def all_of(cls, values: list[str]) -> ClassProperty:
        return ClassProperty(
            subject="class_property", matcher=AllOf[str](values=values)
        )

    @classmethod
    def none_of(cls, values: list[str]) -> ClassProperty:
        return ClassProperty(
            subject="class_property", matcher=NoneOf[str](values=values)
        )


class ClassPropertyValue(SubjectFilter):
    subject: Literal["class_property_value"] = "class_property_value"
    matcher: Union[AnyOf[str], AllOf[str], NoneOf[str]]

    @classmethod
    def any_of(cls, values: list[str]) -> ClassPropertyValue:
        return ClassPropertyValue(
            subject="class_property_value", matcher=AnyOf[str](values=values)
        )

    @classmethod
    def all_of(cls, values: list[str]) -> ClassPropertyValue:
        return ClassPropertyValue(
            subject="class_property_value", matcher=AllOf[str](values=values)
        )

    @classmethod
    def none_of(cls, values: list[str]) -> ClassPropertyValue:
        return ClassPropertyValue(
            subject="class_property_value", matcher=NoneOf[str](values=values)
        )


class UpdatedAt(SubjectFilter):
    subject: Literal["updated_at"] = "updated_at"
    matcher: DateRange

    @classmethod
    def between(cls, start: datetime, end: datetime) -> UpdatedAt:
        return UpdatedAt(subject="updated_at", matcher=DateRange(start=start, end=end))

    @classmethod
    def before(cls, end: datetime) -> UpdatedAt:
        return UpdatedAt(subject="updated_at", matcher=DateRange(end=end))

    @classmethod
    def after(cls, start: datetime) -> UpdatedAt:
        return UpdatedAt(subject="updated_at", matcher=DateRange(start=start))


class WorkflowStatus(SubjectFilter):
    subject: Literal["workflow_status"] = "workflow_status"
    matcher: Union[AnyOf[WorkflowStatusType], NoneOf[WorkflowStatusType]]

    @classmethod
    def any_of(cls, values: list[WorkflowStatusType]) -> WorkflowStatus:
        return WorkflowStatus(
            subject="workflow_status", matcher=AnyOf[WorkflowStatusType](values=values)
        )

    @classmethod
    def none_of(cls, values: list[WorkflowStatusType]) -> WorkflowStatus:
        return WorkflowStatus(
            subject="workflow_status", matcher=NoneOf[WorkflowStatusType](values=values)
        )


class WorkflowStage(SubjectFilter):
    subject: Literal["workflow_stage"] = "workflow_stage"
    matcher: Union[AnyOf[str], NoneOf[str]]

    @classmethod
    def any_of(cls, values: list[str]) -> WorkflowStage:
        return WorkflowStage(
            subject="workflow_stage", matcher=AnyOf[str](values=values)
        )

    @classmethod
    def none_of(cls, values: list[str]) -> WorkflowStage:
        return WorkflowStage(
            subject="workflow_stage", matcher=NoneOf[str](values=values)
        )


class GroupFilter(BaseModel):
    conjunction: Literal["and", "or"] = "and"
    filters: List[Union[GroupFilter, SubjectFilter]]

    @field_validator("filters")
    def validate_filters(
        cls, value: List[GroupFilter | SubjectFilter]
    ) -> List[GroupFilter | SubjectFilter]:
        if len(value) < 2:
            raise ValueError("Must provide at least two filters.")
        return value

    def __and__(self, other: GroupFilter | SubjectFilter) -> GroupFilter:
        if isinstance(other, GroupFilter):
            if self.conjunction == "and" and other.conjunction == "and":
                return GroupFilter(
                    conjunction="and", filters=[*self.filters, *other.filters]
                )
            return GroupFilter(conjunction="and", filters=[self, other])
        if isinstance(other, SubjectFilter):
            if self.conjunction == "and":
                return GroupFilter(conjunction="and", filters=[*self.filters, other])
            return GroupFilter(conjunction="and", filters=[self, other])

    def __or__(self, other: GroupFilter | SubjectFilter) -> GroupFilter:
        if isinstance(other, GroupFilter):
            if self.conjunction == "or" and other.conjunction == "or":
                return GroupFilter(
                    conjunction="or", filters=[*self.filters, *other.filters]
                )
            return GroupFilter(conjunction="or", filters=[self, other])
        if isinstance(other, SubjectFilter):
            if self.conjunction == "or":
                return GroupFilter(conjunction="or", filters=[*self.filters, other])
            return GroupFilter(conjunction="or", filters=[self, other])
