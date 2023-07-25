from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import Field, root_validator

from darwin.future.data_objects.typing import UnknownType
from darwin.future.pydantic_base import DefaultDarwin


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
    instructions: str = Field(min_length=0)

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
    source_stage_id: Optional[UUID]
    target_stage_id: Optional[UUID]

    @root_validator(pre=True)
    def _one_or_both_must_exist(cls, values: dict) -> dict:
        if not values["source_stage_id"] and not values["target_stage_id"]:
            raise ValueError("One or both of source_stage_id and target_stage_id must be defined")

        return values


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
    DISCARD = "discard"
    MODEL = "model"
    WEBHOOK = "webhook"
    ARCHIVE = "archive"
    CONSENSUS_TEST = "consensus_test"
    CONSENSUS_ENTRYPOINT = "consensus_entrypoint"


class WFUser(DefaultDarwin):
    stage_id: UUID
    user_id: int


class WFStageConfig(DefaultDarwin):
    # ! NB: We may be able to remove many of these attributes
    url: Optional[str]
    x: Optional[int]
    y: Optional[int]

    dataset_id: Optional[int]
    model_type: Optional[str]

    parallel_stage_ids: Optional[List[UUID]]
    readonly: bool

    # Included, and type known, but potentially not involved in backend
    auto_instantiate: bool
    include_annotations: bool
    initial: bool
    retry_if_fails: bool
    rules: List
    skippable: bool
    test_stage_id: Optional[UUID]

    # unsure of needs for these, so they here for future proofing
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

    id: UUID
    name: str
    team_id: int

    inserted_at: datetime
    updated_at: datetime

    dataset: Optional[WFDataset]
    stages: List[WFStage]

    thumbnails: List[str]


class WorkflowListValidator(DefaultDarwin):
    list: List[Workflow]
