from typing import List, Optional

from pydantic import BaseModel, validator

from darwin.future.data_objects import validators as darwin_validators


class DefaultDarwin(BaseModel):
    class Config:
        validate_assignment = True


class Release(DefaultDarwin):
    name: str

    _name_validator = validator("name", allow_reuse=True)(darwin_validators.parse_name)


class Dataset(DefaultDarwin):
    name: str
    id: Optional[int] = None
    releases: Optional[List[Release]] = None
    _name_validator = validator("name", allow_reuse=True)(darwin_validators.parse_name)
    _id_validator = validator("id", allow_reuse=True)(darwin_validators.is_positive)


class TeamMember(DefaultDarwin):
    name: str


class Team(DefaultDarwin):
    name: str
    datasets: Optional[List[Dataset]] = None
    members: Optional[List[TeamMember]] = None
    _name_validator = validator("name", allow_reuse=True)(darwin_validators.parse_name)
