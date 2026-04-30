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


class MetadataTriggerCondition(DefaultDarwin):
    """
    Metadata-side trigger condition: identifies parent values by name.
    Parsed from ``.v7/metadata.json``; converted to :class:`ApiTriggerCondition`
    by the importer.
    """

    type: Literal["value_match", "any_value"]
    values: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def _validate_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        trigger_type = data.get("type")
        values = data.get("values")
        if trigger_type == "any_value":
            if values:
                raise ValueError(
                    "trigger_condition.values must be empty/None for 'any_value'"
                )
        elif trigger_type == "value_match":
            if not values:
                raise ValueError(
                    "trigger_condition.values (parent value names) must be set "
                    "for 'value_match'"
                )
        return data


class ApiTriggerCondition(DefaultDarwin):
    """
    API-side trigger condition: identifies parent values by UUID
    (``property_value_ids``). This is the shape stored on
    :attr:`FullProperty.trigger_condition` and the only shape sent to the BE.
    """

    type: Literal["value_match", "any_value"]
    property_value_ids: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def _validate_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        trigger_type = data.get("type")
        property_value_ids = data.get("property_value_ids")
        if trigger_type == "any_value":
            if property_value_ids:
                raise ValueError(
                    "trigger_condition.property_value_ids must be empty/None for 'any_value'"
                )
        elif trigger_type == "value_match":
            if not property_value_ids:
                raise ValueError(
                    "trigger_condition.property_value_ids (parent value UUIDs) "
                    "must be set for 'value_match'"
                )
        return data

    def to_api_payload(self) -> Dict[str, Any]:
        """
        Return ``{"type": "any_value"}`` or
        ``{"type": "value_match", "property_value_ids": [...]}``.
        """
        payload: Dict[str, Any] = {"type": self.type}
        if self.type == "value_match":
            payload["property_value_ids"] = list(self.property_value_ids or [])
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
    trigger_condition: Optional[ApiTriggerCondition] = None

    def to_create_endpoint(
        self,
    ) -> dict:
        if (
            self.granularity != PropertyGranularity.item
            and self.annotation_class_id is None
        ):
            raise ValueError("annotation_class_id must be set")

        # Nesting fields are coherent: all three set, or none set.
        nesting_set = (
            self.parent_property_id is not None,
            self.trigger_condition is not None,
        )
        if any(nesting_set) and not all(nesting_set):
            raise ValueError(
                "parent_property_id and trigger_condition must both be set or "
                "both be None. Resolve parent_name to a parent_property_id first."
            )
        if self.parent_name is not None and self.parent_property_id is None:
            raise ValueError(
                "parent_name set without parent_property_id; the importer "
                "resolves parent_name via _resolve_parent_for_create before "
                "calling to_create_endpoint."
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
        if "parent_property_id" in updated_base:
            del updated_base["parent_property_id"]
        if "trigger_condition" in updated_base:
            del updated_base["trigger_condition"]
        return self.id, updated_base


class MetadataProperty(FullProperty):
    """
    Variant of :class:`FullProperty` used to parse properties as declared in
    ``.v7/metadata.json``.

    The only difference is the trigger-condition shape: ``.v7/metadata.json``
    identifies parent values by **name** (:class:`MetadataTriggerCondition`),
    whereas the REST API identifies them by **UUID**
    (:class:`ApiTriggerCondition`). The importer converts metadata triggers
    to API triggers via name-to-UUID resolution before calling
    ``client.create_property``.

    A ``MetadataProperty`` is parse-only: ``to_create_endpoint`` /
    ``to_update_endpoint`` should not be called on it directly.
    """

    trigger_condition: Optional[MetadataTriggerCondition] = None  # type: ignore[assignment]


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
        properties (List[MetadataProperty]): List of all properties for the
            class — name-based ``trigger_condition`` (metadata-side shape).
    """

    name: str
    type: str
    description: Optional[str] = None
    color: Optional[str] = None
    sub_types: Optional[List[str]] = None
    granularity: PropertyGranularity = PropertyGranularity("section")
    properties: List[MetadataProperty]

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
