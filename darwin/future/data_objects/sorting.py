from typing import Literal, Optional

from pydantic import BaseModel, Field, root_validator


class SortingMethods(BaseModel):
    accuracy: Optional[Literal["asc", "desc"]] = Field(None)
    byte_size: Optional[Literal["asc", "desc"]] = Field(None)
    id: Optional[Literal["asc", "desc"]] = Field(None)
    map: Optional[Literal["asc", "desc"]] = Field(None)
    name: Optional[Literal["asc", "desc"]] = Field(None)
    priority: Optional[Literal["asc", "desc"]] = Field(None)
    updated_at: Optional[Literal["asc", "desc"]] = Field(None)

    @root_validator(pre=True)
    def check_at_least_one_field(cls, values):
        assert any(value is not None for value in values.values())
        return values
