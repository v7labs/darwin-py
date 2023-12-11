from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from pydantic import validator

from darwin.future.data_objects.pydantic_base import DefaultDarwin


class PropertyOption(DefaultDarwin):
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
    type: str
    value: Union[Dict[str, str], str]
    color: str

    @validator("color")
    def validate_rgba(cls, v: str) -> str:
        if not v.startswith("rgba"):
            raise ValueError("Color must be in rgba format")
        return v


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
    type: str
    description: Optional[str]
    required: bool
    slug: Optional[str]
    team_id: Optional[int]
    annotation_class_id: Optional[int]
    property_values: Optional[List[PropertyOption]]
    options: Optional[List[PropertyOption]]


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
