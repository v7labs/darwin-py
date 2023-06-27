from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import validator

from darwin.future.pydantic_base import DefaultDarwin


def validate_uuid(uuid: str) -> bool:
    """
    Validates a uuid string

    Parameters
    ----------
    uuid: str
        - the uuid to validate

    Returns
    ----------
    bool
        - True if the uuid is valid, False otherwise
    """
    try:
        UUID(uuid)
        return True
    except ValueError:
        return False


class WFDataSet(DefaultDarwin):
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

    def __repr__(self) -> str:
        return f"<WFDataSet id={self.id} name={self.name}>"

    _id_validator = validator("id", allow_reuse=True)(validate_uuid)


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

    id: str
    name: str
    source_stage_id: str
    target_stage_id: str

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
    ...  # TODO: implement this class, if it's needed


class WFStageConfig(DefaultDarwin):
    ...  # TODO: implement this class, if it's needed


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

    id: str
    name: str

    type: WFType

    assignable_users: List[WFUser]  # ! Not sure of type
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

    dataset: WFDataSet
    stages: List[WFStage]

    thumbnails: List[str]

    _id_validator = validator("id", allow_reuse=True)(validate_uuid)
