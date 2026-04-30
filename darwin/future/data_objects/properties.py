from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import field_validator, model_validator

from darwin.future.data_objects.pydantic_base import DefaultDarwin

PropertyType = Literal[
    "multi_select",
    "single_select",
    "text",
    "attributes",
    "instance_id",
    "directional_vector",
]


class TriggerCondition(DefaultDarwin):
    """
    Condition that must be met on a parent property for a nested (child) property
    to be visible.

    The condition has two interchangeable representations:

    * ``values``: a list of **parent value names** (strings). This is the shape
      used in ``.v7/metadata.json`` and the preferred representation in
      darwin-py — consistent with how the rest of the SDK identifies properties
      and values by name rather than by server-side UUIDs.
    * ``property_value_ids``: a list of **parent value UUIDs**. This is the
      shape accepted and returned by the REST API; the importer resolves
      ``values`` to UUIDs just-in-time after the parent is created.

    Exactly one of the two must be set when ``type == "value_match"``. Both
    must be empty/None when ``type == "any_value"``.
    """

    type: Literal["value_match", "any_value"]
    property_value_ids: Optional[List[str]] = None
    values: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def _validate_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        trigger_type = data.get("type")
        values = data.get("values")
        property_value_ids = data.get("property_value_ids")
        if trigger_type == "any_value":
            if values:
                raise ValueError(
                    "trigger_condition.values must be empty/None for 'any_value'"
                )
            if property_value_ids:
                raise ValueError(
                    "trigger_condition.property_value_ids must be empty/None for 'any_value'"
                )
        elif trigger_type == "value_match":
            if not values and not property_value_ids:
                raise ValueError(
                    "trigger_condition must set either 'values' (names) or "
                    "'property_value_ids' (UUIDs) for 'value_match'"
                )
        return data

    def to_api_payload(self) -> Dict[str, Any]:
        """
        Return the REST-API wire shape of the trigger condition:

        * ``{"type": "any_value"}``, or
        * ``{"type": "value_match", "property_value_ids": [...]}``

        The SDK-local ``values`` (name-based) field is never sent — callers
        resolve it to UUIDs before calling this. ``property_value_ids`` is
        omitted entirely for ``any_value`` because the BE's OpenAPI schema
        declares it as a non-nullable array: sending ``null`` fails schema
        validation with an opaque 422.
        """
        payload: Dict[str, Any] = {"type": self.type}
        if self.type == "value_match":
            if not self.property_value_ids:
                raise ValueError(
                    "TriggerCondition.to_api_payload requires non-empty "
                    "property_value_ids for 'value_match'. Resolve "
                    "'values' (names) to UUIDs first via "
                    "_resolve_parent_for_create."
                )
            payload["property_value_ids"] = list(self.property_value_ids)
        return payload


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
    parent_name: Optional[str] = None
    parent_property_id: Optional[str] = None
    trigger_condition: Optional[TriggerCondition] = None

    def to_create_endpoint(
        self,
    ) -> dict:
        if (
            self.granularity != PropertyGranularity.item
            and self.annotation_class_id is None
        ):
            raise ValueError("annotation_class_id must be set")
        if (self.parent_property_id is None) != (self.trigger_condition is None):
            raise ValueError(
                "parent_property_id and trigger_condition must both be set or "
                "both be None. If you have a parent_name, resolve it to a "
                "parent_property_id first."
            )
        if self.parent_name is not None and self.parent_property_id is None:
            raise ValueError(
                "parent_name set without parent_property_id. The importer "
                "resolves ``parent_name`` against the destination team's "
                "lookups before calling to_create_endpoint; if you are "
                "constructing FullProperty by hand, set "
                "parent_property_id (UUID) directly."
            )

        include_fields: Dict[str, Any] = {
            "name": True,
            "type": True,
            "required": True,
            "description": True,
            "granularity": True,
        }
        if self.type != "text":
            include_fields["property_values"] = {"__all__": {"value", "color", "type"}}
        if self.granularity != PropertyGranularity.item:
            include_fields["annotation_class_id"] = True
        if self.dataset_ids is not None:
            include_fields["dataset_ids"] = True

        payload = self.model_dump(mode="json", include=include_fields)
        if self.parent_property_id is not None and self.trigger_condition is not None:
            payload["parent_property_id"] = self.parent_property_id
            payload["trigger_condition"] = self.trigger_condition.to_api_payload()
        return payload

    def to_update_endpoint(self) -> Tuple[str, dict]:
        if self.id is None:
            raise ValueError("id must be set")

        updated_base = self.to_create_endpoint()
        updated_base.pop("annotation_class_id", None)  # Can't update this field
        del updated_base["granularity"]  # Can't update this field
        # parent_property_id and trigger_condition are immutable after creation
        updated_base.pop("parent_property_id", None)
        updated_base.pop("trigger_condition", None)
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


PropertyKey = Tuple[str, Optional[int]]


def property_key(prop: "FullProperty") -> PropertyKey:
    return (prop.name, prop.annotation_class_id)
