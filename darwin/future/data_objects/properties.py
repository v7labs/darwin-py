from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, Union

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

TriggerConditionType = Literal["value_match", "any_value"]


class TriggerCondition(DefaultDarwin):
    """
    Condition that must be met on a parent property for a nested (child) property
    to be visible.

    Attributes:
        type: Trigger kind. "value_match" activates the child when one of the
            listed parent values is selected. "any_value" activates the child
            whenever the parent has any value (any option selected or any text
            entered).
        property_value_ids: Parent property value IDs that activate the child.
            Required (non-empty) for "value_match"; must be omitted/empty for
            "any_value".
    """

    type: TriggerConditionType
    property_value_ids: Optional[List[str]] = None

    @model_validator(mode="after")
    def _validate_shape(self) -> "TriggerCondition":
        if self.type == "value_match":
            if not self.property_value_ids:
                raise ValueError(
                    "trigger_condition.property_value_ids must be non-empty for 'value_match'"
                )
        elif self.type == "any_value":
            # An any_value trigger must not carry specific value IDs; such a
            # combination is nonsensical (the child is always visible when the
            # parent has any value, so specific values have no meaning) and is
            # explicitly rejected by the backend changeset.
            if self.property_value_ids:
                raise ValueError(
                    "trigger_condition.property_value_ids must be empty/None for 'any_value'"
                )
        return self


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
    parent_property_id: Optional[str] = None
    trigger_condition: Optional[TriggerCondition] = None

    def to_create_endpoint(
        self,
    ) -> dict:
        include_fields = {
            "name": True,
            "type": True,
            "required": True,
            "description": True,
            "granularity": True,
        }
        if self.type != "text":
            include_fields["property_values"] = {"__all__": {"value", "color", "type"}}
        if self.granularity != PropertyGranularity.item:
            if self.annotation_class_id is None:
                raise ValueError("annotation_class_id must be set")
            include_fields["annotation_class_id"] = True
        if self.dataset_ids is not None:
            include_fields["dataset_ids"] = True

        # Nesting metadata must be consistent: either both are set (child)
        # or both are nil (top-level). The backend rejects inconsistent
        # combinations; we fail fast on the client to surface a clear error.
        if (self.parent_property_id is None) != (self.trigger_condition is None):
            raise ValueError(
                "parent_property_id and trigger_condition must both be set or both be None"
            )

        if self.parent_property_id is not None:
            include_fields["parent_property_id"] = True
        if self.trigger_condition is not None:
            include_fields["trigger_condition"] = True
        return self.model_dump(mode="json", include=include_fields)

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


def _has_non_empty_value(
    definition: "FullProperty",
    selected_values: List["SelectedProperty"],
) -> bool:
    """
    Returns True when the given property has at least one selected value.
    Whitespace-only text is treated as empty.
    """
    if definition.type == "text":
        return any(
            (s.value or "").strip() for s in selected_values if s.value is not None
        )
    return any(s.value for s in selected_values)


def _matches_trigger(
    trigger: TriggerCondition,
    parent_definition: "FullProperty",
    parent_selected_values: List["SelectedProperty"],
) -> bool:
    if not _has_non_empty_value(parent_definition, parent_selected_values):
        return False
    if trigger.type == "any_value":
        return True
    # trigger.type == "value_match"
    if parent_definition.type == "text":
        return False
    trigger_values = set(trigger.property_value_ids or [])
    if not trigger_values:
        return False
    value_id_by_name = {
        pv.value: pv.id
        for pv in (parent_definition.property_values or [])
        if pv.id is not None and pv.value is not None
    }
    return any(
        value_id_by_name.get(s.value or "") in trigger_values
        for s in parent_selected_values
    )


def get_visible_properties(
    annotation_properties: List["SelectedProperty"],
    property_definitions: List["FullProperty"],
) -> List["SelectedProperty"]:
    """
    Filter per-annotation property values to only those whose ancestor chain
    is satisfied (trigger conditions met).

    This mirrors the visibility logic used by the frontend ``VisibilityEngine``
    and the backend ``GetRequiredPropertiesPresence`` path. The export pipeline
    relies on this function to ensure exported files match what the user sees
    in the UI: child values whose parent no longer has the triggering value
    are excluded.

    Parameters
    ----------
    annotation_properties: list of per-annotation ``SelectedProperty`` values
        (as they appear on a single annotation or item).
    property_definitions: the corresponding ``FullProperty`` definitions for
        the team/class. Must include parents of any nested child referenced
        in ``annotation_properties``.

    Returns
    -------
    list of ``SelectedProperty`` that are currently visible, preserving the
    original order.
    """
    if not annotation_properties:
        return []

    definitions_by_id: Dict[str, FullProperty] = {
        d.id: d for d in property_definitions if d.id is not None
    }
    definitions_by_name: Dict[str, FullProperty] = {
        d.name: d for d in property_definitions
    }

    selected_by_parent_name: Dict[str, List[SelectedProperty]] = {}
    for selected in annotation_properties:
        selected_by_parent_name.setdefault(selected.name, []).append(selected)

    visibility_cache: Dict[str, bool] = {}
    # Tracks definitions currently being evaluated on the call stack so that
    # a pathological (cyclic) ``parent_property_id`` graph doesn't cause
    # unbounded recursion. The backend enforces acyclicity on create, but
    # this utility is public and may be invoked on arbitrary inputs.
    visiting: set = set()

    def is_visible(definition: FullProperty) -> bool:
        if definition.id is not None and definition.id in visibility_cache:
            return visibility_cache[definition.id]
        if definition.id is not None and definition.id in visiting:
            # Cycle detected — treat as hidden rather than recursing forever.
            return False

        if definition.id is not None:
            visiting.add(definition.id)
        try:
            if definition.parent_property_id is None:
                result = True
            else:
                parent_definition = definitions_by_id.get(definition.parent_property_id)
                if parent_definition is None or definition.trigger_condition is None:
                    result = False
                elif not is_visible(parent_definition):
                    result = False
                else:
                    result = _matches_trigger(
                        definition.trigger_condition,
                        parent_definition,
                        selected_by_parent_name.get(parent_definition.name, []),
                    )
        finally:
            if definition.id is not None:
                visiting.discard(definition.id)

        if definition.id is not None:
            visibility_cache[definition.id] = result
        return result

    visible: List[SelectedProperty] = []
    for selected in annotation_properties:
        definition = definitions_by_name.get(selected.name)
        # No definition available -> be conservative and keep the value.
        if definition is None or is_visible(definition):
            visible.append(selected)
    return visible
