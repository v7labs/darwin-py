from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, Union

from pydantic import validator

from darwin.future.data_objects.pydantic_base import DefaultDarwin

PropertyType = Literal[
    "multi_select",
    "single_select",
    "text",
    "attributes",
    "instance_id",
    "directional_vector",
]


class PropertyValue(DefaultDarwin):
    """
    Describes a single option for a property

    Attributes:
        value (str): Value of the option
        color (Optional[str]): Color of the option
        type (Optional[str]): Type of the option

    Validators:
        color (validator): Validates that the color is in rgba format
    """

    id: Optional[str]
    position: Optional[int]
    type: Literal["string"] = "string"
    value: Union[Dict[str, str], str]
    color: str = "auto"

    @validator("color")
    def validate_rgba(cls, v: str) -> str:
        if not v.startswith("rgba") and v != "auto":
            raise ValueError("Color must be in rgba format or 'auto'")
        return v

    @validator("value")
    def validate_value(cls, v: Union[Dict[str, str], str]) -> Dict[str, str]:
        """TODO: Replace once the value.value bug is fixed in the API"""
        if isinstance(v, str):
            return {"value": v}
        return v

    def to_update_endpoint(self) -> Tuple[str, dict]:
        if self.id is None:
            raise ValueError("id must be set")
        updated_base = self.dict(exclude={"id", "type"})
        return self.id, updated_base


class FullProperty(DefaultDarwin):
    """
    Describes the property and all of the potential options that are associated with it

    Attributes:
        name (str): Name of the property
        type (str): Type of the property
        required (bool): If the property is required
        options (List[PropertyOption]): List of all options for the property
    """

    id: Optional[str]
    name: str
    type: PropertyType
    description: Optional[str]
    required: bool
    slug: Optional[str]
    team_id: Optional[int]
    annotation_class_id: Optional[int]
    property_values: Optional[List[PropertyValue]]
    options: Optional[List[PropertyValue]]

    def to_create_endpoint(
        self,
    ) -> dict:
        if self.annotation_class_id is None:
            raise ValueError("annotation_class_id must be set")
        return self.dict(
            include={
                "name": True,
                "type": True,
                "required": True,
                "annotation_class_id": True,
                "property_values": {"__all__": {"type", "value", "color"}},
                "description": True,
            }
        )

    def to_update_endpoint(self) -> Tuple[str, dict]:
        if self.id is None:
            raise ValueError("id must be set")
        updated_base = self.to_create_endpoint()
        del updated_base["annotation_class_id"]  # can't update this field
        return self.id, updated_base


class MetaDataClass(DefaultDarwin):
    """
    Metadata.json -> property mapping. Contains all properties for a class contained
    in the metadata.json file. Along with all options for each property that is associated
    with the class.

    Attributes:
        name (str): Name of the class
        type (str): Type of the class
        description (Optional[str]): Description of the class
        color (Optional[str]): Color of the class in the UI
        sub_types (Optional[List[str]]): Sub types of the class
        properties (List[FullProperty]): List of all properties for the class with all options
    """

    name: str
    type: str
    description: Optional[str]
    color: Optional[str]
    sub_types: Optional[List[str]]
    properties: List[FullProperty]

    @classmethod
    def from_path(cls, path: Path) -> List[MetaDataClass]:
        if not path.exists():
            raise FileNotFoundError(f"File {path} does not exist")
        if os.path.isdir(path):
            if os.path.exists(path / ".v7" / "metadata.json"):
                path = path / ".v7" / "metadata.json"
            else:
                raise FileNotFoundError("File metadata.json does not exist in path")
        if path.suffix != ".json":
            raise ValueError(f"File {path} must be a json file")
        with open(path, "r") as f:
            data = json.load(f)
        return [cls(**d) for d in data["classes"]]


class SelectedProperty(DefaultDarwin):
    """
    Selected property for an annotation found inside a darwin annotation

    Attributes:
        frame_index (int): Frame index of the annotation
        name (str): Name of the property
        type (str): Type of the property
        value (str): Value of the property
    """

    frame_index: int
    name: str
    type: str
    value: str
