from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union
from uuid import UUID

from pydantic import validator

from darwin.future.data_objects.typing import UnknownType
from darwin.future.pydantic_base import DefaultDarwin

from .validators import validate_uuid


class WFDataset(DefaultDarwin):
    """
    A class to manage all the information around a dataset on the darwin platform,
    including validation

    Attributes
    ----------
    id: int
    name: str
    instructions: str

    Methods
    ----------
    __int__: returns the id of the dataset
    __str__: returns the name of the dataset
    __repr__: returns a string representation of the dataset
    """

    id: int
    name: str
    instructions: str

    def __int__(self) -> int:
        return self.id

    def __str__(self) -> str:
        return self.name


class WFEdge(DefaultDarwin):
    """
    A workflow edge

    Attributes
    ----------

    id: str
    name: str
    source_stage_id: str
    target_stage_id: str
    """

    id: UUID
    name: str
    source_stage_id: UUID
    target_stage_id: UUID

    _id_validator = validator("id", allow_reuse=True)(validate_uuid)
    _source_stage_id_validator = validator("source_stage_id", allow_reuse=True)(validate_uuid)
    _target_stage_id_validator = validator("target_stage_id", allow_reuse=True)(validate_uuid)


class WFType(Enum):
    """
    The type of workflow stage (Enum)

    Enumerations
    ----------
    DATASET: str
    ANNOTATE: str
    REVIEW: str
    COMPLETE: str
    """

    # TODO: There may be more types
    DATASET = "dataset"
    ANNOTATE = "annotate"
    REVIEW = "review"
    COMPLETE = "complete"


class WFUser(DefaultDarwin):
    stage_id: UUID
    user_id: int


class WFStageConfig(DefaultDarwin):
    # ! NB: We may be able to remove many of these attributes
    url: Optional[str]
    x: int
    y: int

    dataset_id: int
    model_type: str

    parallel_stage_ids: Optional[List[UUID]]
    readonly: bool

    auto_instantiate: bool
    include_annotations: bool
    initial: bool
    retry_if_fails: bool
    rules: List
    skippable: bool
    test_stage_id: Optional[UUID]

    #
    allowed_class_ids: UnknownType
    annotation_group_id: UnknownType
    assignable_to: UnknownType
    authorization_header: UnknownType
    champion_stage_id: UnknownType
    class_mapping: List
    from_non_default_v1_template: UnknownType
    iou_thresholds: UnknownType
    model_id: UnknownType
    threshold: UnknownType


class WFStage(DefaultDarwin):
    """
    A workflow stage

    Attributes
    ----------
    id: str
    name: str

    type: WFType

    assignable_users: List[WFUser]
    edges: List[WFEdge]
    """

    id: UUID
    name: str

    type: WFType

    assignable_users: List[WFUser]
    edges: List[WFEdge]

    _id_validator = validator("id", allow_reuse=True)(validate_uuid)


class Workflow(DefaultDarwin):
    """
    A class to manage all the information around a workflow on the darwin platform,
    including validation

    Attributes
    ----------
    id: str
    name: str
    team_id: int

    inserted_at: datetime
    updated_at: datetime

    dataset: WFDataSet
    stages: List[WFStage]

    thumbnails: List[str]
    """

    id: str
    name: str
    team_id: int

    inserted_at: datetime
    updated_at: datetime

    dataset: WFDataset
    stages: List[WFStage]

    thumbnails: List[str]

    _id_validator = validator("id", allow_reuse=True)(validate_uuid)
