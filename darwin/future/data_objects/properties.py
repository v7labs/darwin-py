from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union

from pydantic import field_validator

from darwin.future.data_objects.pydantic_base import DefaultDarwin

PropertyType = Literal[
    "multi_select",
    "single_select",
    "text",
    "attributes",
    "instance_id",
    "directional_vector",
]


class PropertyGranularity(str, Enum):
    section = "section"
    annotation = "annotation"
    item = "item"


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

    id: Optional[str] = None
    type: Literal["string"] = "string"
    value: Optional[str] = None
    color: str = "auto"

    @field_validator("color")
    @classmethod
    def validate_rgba(cls, v: str) -> str:
        if not v.startswith("rgba") and v != "auto":
            raise ValueError("Color must be in rgba format or 'auto'")
        return v

    def to_update_endpoint(self) -> Tuple[str, dict]:
        if self.id is None:
            raise ValueError("id must be set")
        updated_base = self.model_dump(exclude={"id", "type"})
        return self.id, updated_base


class FullProperty(DefaultDarwin):
    """
    Describes the property and all of the potential options that are associated with it

    Attributes:
        name (str): Name of the property
        type (str): Type of the property
        required (bool): If the property is required
        options (List[PropertyOption]): List of all options for the property
        granularity (PropertyGranularity): Granularity of the property

    """

    id: Optional[str] = None
    position: Optional[int] = None
    name: str
    type: PropertyType
    description: Optional[str] = None
    required: bool
    slug: Optional[str] = None
    team_id: Optional[int] = None
    annotation_class_id: Optional[int] = None
    property_values: Optional[List[PropertyValue]] = None
    granularity: PropertyGranularity
    dataset_ids: Optional[List[int]] = None
    options: Optional[List[PropertyValue]] = None
    granularity: PropertyGranularity = PropertyGranularity("section")

    def to_create_endpoint(
        self,
    ) -> dict:
        include_fields = {
            "name": True,
            "type": True,
            "required": True,
            "property_values": {"__all__": {"value", "color", "type"}},
            "description": True,
            "granularity": True,
        }
        if self.granularity != PropertyGranularity.item:
            if self.annotation_class_id is None:
                raise ValueError("annotation_class_id must be set")
            include_fields["annotation_class_id"] = True
        if self.dataset_ids is not None:
            include_fields["dataset_ids"] = True
        return self.model_dump(mode="json", include=include_fields)

    def to_update_endpoint(self) -> Tuple[str, dict]:
        if self.id is None:
            raise ValueError("id must be set")

        updated_base = self.to_create_endpoint()
        updated_base.pop("annotation_class_id", None)  # Can't update this field
        del updated_base["granularity"]  # Can't update this field
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
        granularity:(PropertyGranularity): Granularity of the property
        properties (List[FullProperty]): List of all properties for the class with all options
    """

    name: str
    type: str
    description: Optional[str] = None
    color: Optional[str] = None
    sub_types: Optional[List[str]] = None
    granularity: PropertyGranularity = PropertyGranularity("section")
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
        return [cls.model_validate(d) for d in data["classes"]]


class SelectedProperty(DefaultDarwin):
    """
    Selected property for an annotation found inside a darwin annotation

    Attributes:
        frame_index (int | str): Frame index of the annotation
        int for section-level properties, and "global" for annotation-level properties
        name (str): Name of the property
        type (str | None): Type of the property (if it exists)
        value (str): Value of the property
    """

    frame_index: Optional[Union[int, str]] = None
    name: str
    type: Optional[str] = None
    value: Optional[str] = None
