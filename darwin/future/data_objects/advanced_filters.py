from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, validator

T = TypeVar("T")

FileType = Literal["image", "video", "pdf", "dicom"]
IssueType = Literal["comment"]
ProcessingStatusType = Literal["cancelled", "error", "uploading", "uploading_confirmed", "processing", "complete"]
WorkflowStatusType = Literal["new", "annotate", "review", "complete"]


class GroupFilter(BaseModel, ABC):
    conjuction: Literal['and', 'or'] = 'and'
    filters: List[GroupFilter | SubjectFilter]


class SubjectFilter(BaseModel, ABC):
    subject: str
    matcher: BaseMatcher
    
class BaseMatcher(BaseModel, ABC):
    name: str
    
# Subject Filters
class AnnotationClassFilter(SubjectFilter):
    subject: Literal['annotation_class'] = 'annotation_class'
    matcher: AnyOfMatcher[int] | AllOfMatcher[int] | NoneOfMatcher[int]
    

class ArchivedFilter(SubjectFilter):
    subject: Literal['archived'] = 'archived'
    matcher: EqualsMatcher[bool]

class AssigneeFilter(SubjectFilter):
    subject: Literal['assignee'] = 'assignee'
    matcher: AnyOfMatcher[int] | AllOfMatcher[int] | NoneOfMatcher[int]
    
    
class CreatedAtFilter(SubjectFilter):
    subject: Literal['created_at'] = 'created_at'
    matcher: DateRangeMatcher
    
    
class CurrentAssigneeFilter(SubjectFilter):
    subject: Literal['current_assignee'] = 'current_assignee'
    matcher: AnyOfMatcher[int] | NoneOfMatcher[int]
    

class FileTypeFilter(SubjectFilter):
    subject: Literal['file_type'] = 'file_type'
    matcher: AnyOfMatcher[FileType] | AllOfMatcher[FileType] | NoneOfMatcher[FileType]
    

class FolderPathFilter(SubjectFilter):
    subject: Literal['folder_path'] = 'folder_path'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str] | PrefixMatcher | SuffixMatcher
    
    
class IdFilter(SubjectFilter):
    subject: Literal['id'] = 'id'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str]
    

class IssueFilter(SubjectFilter):
    subject: Literal['issue'] = 'issue'
    matcher: AnyOfMatcher[IssueType] | NoneOfMatcher[IssueType]
    

class ItemNameFilter(SubjectFilter):
    subject: Literal['item_name'] = 'item_name'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str] | PrefixMatcher | SuffixMatcher | ContainsMatcher | NotContainsMatcher


class ProcessingStatusFilter(SubjectFilter):
    subject: Literal['processing_status'] = 'processing_status'
    matcher: AnyOfMatcher[ProcessingStatusType] | NoneOfMatcher[ProcessingStatusType]
    
    
class UpdatedAtFilter(SubjectFilter):
    subject: Literal['updated_at'] = 'updated_at'
    matcher: DateRangeMatcher
    
    
    
class WorkflowStatusFilter(SubjectFilter):
    subject: Literal['workflow_status'] = 'workflow_status'
    matcher: AnyOfMatcher[WorkflowStatusType] | NoneOfMatcher[WorkflowStatusType]
    
    
class WorkflowStageFilter(SubjectFilter):
    subject: Literal['workflow_stage'] = 'workflow_stage'
    matcher: AnyOfMatcher[str] | NoneOfMatcher[str]
    

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
    
