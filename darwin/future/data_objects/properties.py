from __future__ import annotations

import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union

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

    type: TriggerConditionType
    property_value_ids: Optional[List[str]] = None
    values: Optional[List[str]] = None

    @model_validator(mode="before")
    @classmethod
    def _validate_shape(cls, data: Any) -> Any:
        # ``mode="before"`` runs for every construction path — ``model_validate``
        # with a raw dict, direct ``TriggerCondition(type=..., ...)`` keyword
        # construction, and nested validation where Pydantic may hand us an
        # already-built instance. Only the dict path needs cross-field checks;
        # the others have already been validated once.
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
        if self.property_value_ids:
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
    # Nesting metadata. ``parent_name`` is the darwin-py / ``.v7/metadata.json``
    # representation (identify the parent by its property name, consistent
    # with how the SDK identifies everything else). ``parent_property_id`` is
    # populated from REST API responses and sent back on create — it is
    # resolved from ``parent_name`` by the importer after the parent has been
    # created on the server.
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
        # A nested property must carry both an API-ready parent UUID and a
        # trigger condition. ``parent_name`` is the SDK-local representation
        # and must be resolved to ``parent_property_id`` before calling this.
        if (self.parent_property_id is None) != (self.trigger_condition is None):
            raise ValueError(
                "parent_property_id and trigger_condition must both be set or "
                "both be None. If you have a parent_name, resolve it to a "
                "parent_property_id first."
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
        if self.parent_property_id is not None:
            include_fields["parent_property_id"] = True

        payload = self.model_dump(mode="json", include=include_fields)
        if self.trigger_condition is not None:
            # ``TriggerCondition.to_api_payload`` owns the wire shape so
            # ``to_create_endpoint`` doesn't have to reach into a nested
            # model's representation.
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


# Properties are identified within a team by the tuple
# ``(annotation_class_id, name)`` — item-level properties use ``None`` for the
# class id. This matches ``TeamPropertyLookups.annotation_properties`` (keyed
# by ``(name, class_id)``) and ``item_properties`` (keyed by ``name``). Code
# that needs to locate or deduplicate property definitions should use this
# helper rather than inventing its own keying.
PropertyKey = Tuple[Optional[int], str]


def property_key(prop: "FullProperty") -> PropertyKey:
    return (prop.annotation_class_id, prop.name)


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


def _trigger_value_names(
    trigger: TriggerCondition, parent_definition: "FullProperty"
) -> Set[str]:
    """
    Return the set of parent **value names** that activate the trigger,
    resolved from whichever representation the trigger carries. Callers
    should only invoke this when ``trigger.type == "value_match"``.

    The SDK-native ``values`` list wins when present. If the trigger was
    loaded from an API response and only carries ``property_value_ids``,
    each UUID is resolved to its value name via the parent's
    ``property_values``. UUIDs that don't match any parent value are
    silently dropped — a safety net for stale/mismatched definitions.
    """
    if trigger.values:
        return set(trigger.values)
    if not trigger.property_value_ids:
        return set()
    name_by_id = {
        pv.id: pv.value
        for pv in (parent_definition.property_values or [])
        if pv.id is not None and pv.value is not None
    }
    return {name_by_id[vid] for vid in trigger.property_value_ids if vid in name_by_id}


def _matches_trigger(
    trigger: TriggerCondition,
    parent_definition: "FullProperty",
    parent_selected_values: List["SelectedProperty"],
) -> bool:
    if not _has_non_empty_value(parent_definition, parent_selected_values):
        return False
    if trigger.type == "any_value":
        return True
    if parent_definition.type == "text":
        return False
    expected_names = _trigger_value_names(trigger, parent_definition)
    return bool(expected_names) and any(
        s.value in expected_names for s in parent_selected_values
    )


def _resolve_parent_definition(
    definition: "FullProperty",
    definitions_by_key: Dict[PropertyKey, "FullProperty"],
    definitions_by_id: Dict[str, "FullProperty"],
) -> Optional["FullProperty"]:
    """
    Locate the parent of ``definition`` in the provided lookups.

    Name-based resolution wins (darwin-py convention). UUID-based resolution
    is a fallback for properties loaded from API responses where only
    ``parent_property_id`` is hydrated.
    """
    if definition.parent_name is not None:
        return definitions_by_key.get(
            (definition.annotation_class_id, definition.parent_name)
        )
    if definition.parent_property_id is not None:
        return definitions_by_id.get(definition.parent_property_id)
    return None


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

    definitions_by_key: Dict[PropertyKey, FullProperty] = {
        property_key(d): d for d in property_definitions
    }
    definitions_by_id: Dict[str, FullProperty] = {
        d.id: d for d in property_definitions if d.id is not None
    }
    # Bare-name fallback used when matching ``SelectedProperty`` (which has
    # no class scope) to a definition. If two definitions share a name
    # across scopes we can't disambiguate here, so we keep the first to
    # preserve deterministic behaviour rather than silently shadowing.
    definitions_by_name: Dict[str, FullProperty] = {}
    for d in property_definitions:
        definitions_by_name.setdefault(d.name, d)

    selected_by_parent_name: Dict[str, List[SelectedProperty]] = {}
    for selected in annotation_properties:
        selected_by_parent_name.setdefault(selected.name, []).append(selected)

    # Cache + in-flight set are keyed by ``(annotation_class_id, name)`` so
    # a class-level and item-level property with the same name don't share
    # a cache slot. The in-flight set defends against pathological cyclic
    # graphs: the backend rejects them on create, but this utility is
    # public and may see arbitrary inputs.
    visibility_cache: Dict[PropertyKey, bool] = {}
    visiting: Set[PropertyKey] = set()

    def is_visible(definition: FullProperty) -> bool:
        key = property_key(definition)
        if key in visibility_cache:
            return visibility_cache[key]
        if key in visiting:
            return False

        visiting.add(key)
        try:
            if definition.parent_name is None and definition.parent_property_id is None:
                result = True
            else:
                parent_definition = _resolve_parent_definition(
                    definition, definitions_by_key, definitions_by_id
                )
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
            visiting.discard(key)

        visibility_cache[key] = result
        return result

    visible: List[SelectedProperty] = []
    for selected in annotation_properties:
        definition = definitions_by_name.get(selected.name)
        # No definition available -> be conservative and keep the value.
        if definition is None or is_visible(definition):
            visible.append(selected)
    return visible
