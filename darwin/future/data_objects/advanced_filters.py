from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import Generic, List, Literal, Optional, Self, TypeVar, cast

from pydantic import BaseModel, validator

T = TypeVar("T")

FileType = Literal["image", "video", "pdf", "dicom"]
IssueType = Literal["comment"]
ProcessingStatusType = Literal["cancelled", "error", "uploading", "uploading_confirmed", "processing", "complete"]
WorkflowStatusType = Literal["new", "annotate", "review", "complete"]


class GroupFilter(BaseModel, ABC):
    conjuction: Literal['and', 'or'] = 'and'
    filters: List[GroupFilter | SubjectFilter]
    
    def __iadd__(self, other: GroupFilter) -> Self:
        self.filters.append(other)
        return self
    

class SubjectFilter(BaseModel, ABC):
    subject: str
    matcher: BaseMatcher
    
    def __add__(self, other: SubjectFilter) -> GroupFilter:
        return GroupFilter(conjuction='and', filters=[self, other])
    
    def __or__(self, other: SubjectFilter) -> GroupFilter:
        return GroupFilter(conjuction='or', filters=[self, other])
    
    def __and__(self, other: SubjectFilter) -> GroupFilter:
        return GroupFilter(conjuction='and', filters=[self, other])
    
class BaseMatcher(BaseModel, ABC):
    name: str
    
# Subject Filters
class AnnotationClassFilter(SubjectFilter):
    subject: Literal['annotation_class'] = 'annotation_class'
    matcher: AnyOfMatcher[int] | AllOfMatcher[int] | NoneOfMatcher[int]
    
    def __init__(self, any_of: Optional[List[int]] = None, all_of: Optional[List[int]] = None, none_of: Optional[List[int]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[int](values=any_of)
        elif all_of is not None:
            self.matcher = AllOfMatcher[int](values=all_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[int](values=none_of)
        else:
            raise ValueError('Must specify one of any_of, all_of, or none_of')

class ArchivedFilter(SubjectFilter):
    subject: Literal['archived'] = 'archived'
    matcher: EqualsMatcher[bool]
    
    def __init__(self, value: bool):
        self.matcher = EqualsMatcher[bool](value=value)

class AssigneeFilter(SubjectFilter):
    subject: Literal['assignee'] = 'assignee'
    matcher: AnyOfMatcher[int] | AllOfMatcher[int] | NoneOfMatcher[int]
    
    def __init__(self, any_of: Optional[List[int]] = None, all_of: Optional[List[int]] = None, none_of: Optional[List[int]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[int](values=any_of)
        elif all_of is not None:
            self.matcher = AllOfMatcher[int](values=all_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[int](values=none_of)
        else:
            raise ValueError('Must specify one of any_of, all_of, or none_of')
    
class CreatedAtFilter(SubjectFilter):
    subject: Literal['created_at'] = 'created_at'
    matcher: DateRangeMatcher
    
    def __init__(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        self.matcher = DateRangeMatcher(start=start, end=end)
    
class CurrentAssigneeFilter(SubjectFilter):
    subject: Literal['current_assignee'] = 'current_assignee'
    matcher: AnyOfMatcher[int] | NoneOfMatcher[int]
    
    def __init__(self, any_of: Optional[List[int]] = None, none_of: Optional[List[int]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[int](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[int](values=none_of)
        else:
            raise ValueError('Must specify one of any_of or none_of')

class FileTypeFilter(SubjectFilter):
    subject: Literal['file_type'] = 'file_type'
    matcher: AnyOfMatcher[FileType] | AllOfMatcher[FileType] | NoneOfMatcher[FileType]
    
    def __init__(self, any_of: Optional[List[FileType]] = None, all_of: Optional[List[FileType]] = None, none_of: Optional[List[FileType]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[FileType](values=any_of)
        elif all_of is not None:
            self.matcher = AllOfMatcher[FileType](values=all_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[FileType](values=none_of)
        else:
            raise ValueError('Must specify one of any_of, all_of, or none_of')

class FolderPathFilter(SubjectFilter):
    subject: Literal['folder_path'] = 'folder_path'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str] | PrefixMatcher | SuffixMatcher
    
    def __init__(self, any_of: Optional[List[str]] = None, none_of: Optional[List[str]] = None, prefix: Optional[str] = None, suffix: Optional[str] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[str](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[str](values=none_of)
        elif prefix is not None:
            self.matcher = PrefixMatcher(value=prefix)
        elif suffix is not None:
            self.matcher = SuffixMatcher(value=suffix)
        else:
            raise ValueError('Must specify one of any_of, none_of, prefix, or suffix')
    
class IdFilter(SubjectFilter):
    subject: Literal['id'] = 'id'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str]
    
    def __init__(self, any_of: Optional[List[str]] = None, none_of: Optional[List[str]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[str](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[str](values=none_of)
        else:
            raise ValueError('Must specify one of any_of or none_of')

class IssueFilter(SubjectFilter):
    subject: Literal['issue'] = 'issue'
    matcher: AnyOfMatcher[IssueType] | NoneOfMatcher[IssueType]
    
    def __init__(self, any_of: Optional[List[IssueType]] = None, none_of: Optional[List[IssueType]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[IssueType](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[IssueType](values=none_of)
        else:
            raise ValueError('Must specify one of any_of or none_of')

class ItemNameFilter(SubjectFilter):
    subject: Literal['item_name'] = 'item_name'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str] | PrefixMatcher | SuffixMatcher | ContainsMatcher | NotContainsMatcher

    def __init__(self, any_of: Optional[List[str]] = None, none_of: Optional[List[str]] = None, prefix: Optional[str] = None, suffix: Optional[str] = None, contains: Optional[str] = None, not_contains: Optional[str] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[str](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[str](values=none_of)
        elif prefix is not None:
            self.matcher = PrefixMatcher(value=prefix)
        elif suffix is not None:
            self.matcher = SuffixMatcher(value=suffix)
        elif contains is not None:
            self.matcher = ContainsMatcher(value=contains)
        elif not_contains is not None:
            self.matcher = NotContainsMatcher(value=not_contains)
        else:
            raise ValueError('Must specify one of any_of, none_of, prefix, suffix, contains, or not_contains')

class ProcessingStatusFilter(SubjectFilter):
    subject: Literal['processing_status'] = 'processing_status'
    matcher: AnyOfMatcher[ProcessingStatusType] | NoneOfMatcher[ProcessingStatusType]
    
    def __init__(self, any_of: Optional[List[ProcessingStatusType]] = None, none_of: Optional[List[ProcessingStatusType]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[ProcessingStatusType](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[ProcessingStatusType](values=none_of)
        else:
            raise ValueError('Must specify one of any_of or none_of')
    
class UpdatedAtFilter(SubjectFilter):
    subject: Literal['updated_at'] = 'updated_at'
    matcher: DateRangeMatcher
    
    def __init__(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        self.matcher = DateRangeMatcher(start=start, end=end)
    
    
class WorkflowStatusFilter(SubjectFilter):
    subject: Literal['workflow_status'] = 'workflow_status'
    matcher: AnyOfMatcher[WorkflowStatusType] | NoneOfMatcher[WorkflowStatusType]
    
    def __init__(self, any_of: Optional[List[WorkflowStatusType]] = None, none_of: Optional[List[WorkflowStatusType]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[WorkflowStatusType](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[WorkflowStatusType](values=none_of)
        else:
            raise ValueError('Must specify one of any_of or none_of')
    
class WorkflowStageFilter(SubjectFilter):
    subject: Literal['workflow_stage'] = 'workflow_stage'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str]
    
    def __init__(self, any_of: Optional[List[str]] = None, none_of: Optional[List[str]] = None):
        if any_of is not None:
            self.matcher = AnyOfMatcher[str](values=any_of)
        elif none_of is not None:
            self.matcher = NoneOfMatcher[str](values=none_of)
        else:
            raise ValueError('Must specify one of any_of or none_of')

# Matchers
class AnyOfMatcher(BaseMatcher, Generic[T]):
    name: Literal['any_of'] = 'any_of'
    values: List[T]
    
    @validator('values')
    def validate_any_of(cls, value):
        if len(value) < 2:
            raise ValueError("Must provide at least two values for 'any_of' matcher.")
        return value
    
class AllOfMatcher(BaseMatcher, Generic[T]):
    name: Literal['all_of'] = 'all_of'
    values: List[T]
    
    @validator('values')
    def validate_all_of(cls, value):
        if len(value) < 1:
            raise ValueError("Must provide at least a value for 'all_of' matcher.")
        return value
    
class NoneOfMatcher(BaseMatcher, Generic[T]):
    name: Literal['none_of'] = 'none_of'
    values: List[T]
    
    @validator('values')
    def validate_none_of(cls, value):
        if len(value) < 1:
            raise ValueError("Must provide at least a value for 'none_of' matcher.")
        return value

class EqualsMatcher(BaseMatcher, Generic[T]):
    name: Literal['equals'] = 'equals'
    value: T
    
class DateRangeMatcher(BaseModel):
    name: str = 'date_range'
    start: Optional[datetime]
    end: Optional[datetime]

    @validator('start', 'end')
    def validate_date_range(cls, value, values):
        if not values.get('start') and not values.get('end'):
            raise ValueError("At least one of 'start' or 'end' must be provided.")
        return value
    
class PrefixMatcher(BaseMatcher):
    name: Literal['prefix'] = 'prefix'
    value: str

class SuffixMatcher(BaseMatcher):
    name: Literal['suffix'] = 'suffix'
    value: str

class ContainsMatcher(BaseMatcher):
    name: Literal['contains'] = 'contains'
    value: str

class NotContainsMatcher(BaseMatcher):
    name: Literal['not_contains'] = 'not_contains'
    value: str
    
    

