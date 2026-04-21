"""Unit tests for nested-property SDK support (parent_name, trigger_condition,
topological sort, name-to-UUID resolution, and visibility filtering).
"""

import json
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock

import pytest

import darwin.datatypes as dt
from darwin.datatypes import TeamPropertyLookups, parse_property_classes
from darwin.future.data_objects.properties import (
    FullProperty,
    MetaDataClass,
    PropertyGranularity,
    PropertyValue,
    SelectedProperty,
    TriggerCondition,
    get_visible_properties,
)
from darwin.importer.importer import (
    _enrich_properties_with_metadata_values,
    _import_properties,
    _resolve_parent_for_create,
    _topologically_sort_properties_to_create,
)


def _make_property(
    *,
    name: str,
    id_: Optional[str] = None,
    type_: str = "single_select",
    property_values: Optional[List[PropertyValue]] = None,
    parent_name: Optional[str] = None,
    trigger_condition: Optional[TriggerCondition] = None,
    annotation_class_id: Optional[int] = 1,
    granularity: PropertyGranularity = PropertyGranularity.annotation,
) -> FullProperty:
    return FullProperty(
        id=id_,
        name=name,
        type=type_,
        required=False,
        annotation_class_id=annotation_class_id,
        slug="team-slug",
        property_values=property_values or [],
        granularity=granularity,
        parent_name=parent_name,
        trigger_condition=trigger_condition,
    )


class TestTriggerCondition:
    def test_value_match_requires_values_or_ids(self) -> None:
        with pytest.raises(ValueError):
            TriggerCondition(type="value_match")

    def test_value_match_accepts_values(self) -> None:
        cond = TriggerCondition(type="value_match", values=["Fracture"])
        assert cond.values == ["Fracture"]
        assert cond.property_value_ids is None

    def test_value_match_accepts_property_value_ids(self) -> None:
        cond = TriggerCondition(type="value_match", property_value_ids=["abc-uuid"])
        assert cond.property_value_ids == ["abc-uuid"]
        assert cond.values is None

    def test_value_match_accepts_both_names_and_ids(self) -> None:
        # Both representations coexisting is not an error; callers may
        # hydrate names alongside API-returned UUIDs.
        cond = TriggerCondition(
            type="value_match",
            values=["Fracture"],
            property_value_ids=["abc-uuid"],
        )
        assert cond.values == ["Fracture"]
        assert cond.property_value_ids == ["abc-uuid"]

    def test_any_value_does_not_require_ids_or_values(self) -> None:
        cond = TriggerCondition(type="any_value")
        assert cond.property_value_ids is None
        assert cond.values is None

    def test_any_value_rejects_non_empty_values(self) -> None:
        with pytest.raises(ValueError):
            TriggerCondition(type="any_value", values=["Fracture"])

    def test_any_value_rejects_non_empty_property_value_ids(self) -> None:
        with pytest.raises(ValueError):
            TriggerCondition(type="any_value", property_value_ids=["abc"])

    def test_rejects_unknown_type(self) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            TriggerCondition(type="bogus_type")  # type: ignore[arg-type]

    def test_validator_accepts_already_built_instance(self) -> None:
        # ``mode="before"`` runs on every construction path, including nested
        # validation where Pydantic hands the validator an already-built
        # model. The ``isinstance(data, dict)`` guard must let that through.
        original = TriggerCondition(type="any_value")
        cloned = TriggerCondition.model_validate(original)
        assert cloned.type == "any_value"
        assert cloned.property_value_ids is None
        assert cloned.values is None

    def test_to_api_payload_any_value_omits_property_value_ids(self) -> None:
        assert TriggerCondition(type="any_value").to_api_payload() == {
            "type": "any_value"
        }

    def test_to_api_payload_value_match_emits_property_value_ids(self) -> None:
        trigger = TriggerCondition(
            type="value_match",
            property_value_ids=["v-1", "v-2"],
        )
        assert trigger.to_api_payload() == {
            "type": "value_match",
            "property_value_ids": ["v-1", "v-2"],
        }

    def test_to_api_payload_strips_sdk_local_values(self) -> None:
        # The name-based ``values`` field is an SDK-local convenience. The
        # wire shape never includes it — callers must resolve names to
        # UUIDs (via ``_resolve_parent_for_create``) before serialising.
        trigger = TriggerCondition(
            type="value_match",
            values=["Fracture"],
            property_value_ids=["v-1"],
        )
        assert "values" not in trigger.to_api_payload()


class TestFullPropertyEndpoints:
    def test_create_endpoint_omits_nesting_when_absent(self) -> None:
        prop = _make_property(name="top")
        body = prop.to_create_endpoint()
        assert "parent_property_id" not in body
        assert "parent_name" not in body  # SDK-local field, never sent to API
        assert "trigger_condition" not in body

    def test_create_endpoint_sends_parent_property_id_and_uuid_trigger(self) -> None:
        prop = _make_property(
            name="child",
            parent_name="Parent",
            trigger_condition=TriggerCondition(
                type="value_match",
                values=["Fracture"],
                property_value_ids=["val-uuid"],
            ),
        )
        prop.parent_property_id = "parent-uuid"
        body = prop.to_create_endpoint()
        assert body["parent_property_id"] == "parent-uuid"
        # Name-based ``values`` is an SDK-local convenience and must not leak
        # into the API payload.
        assert body["trigger_condition"] == {
            "type": "value_match",
            "property_value_ids": ["val-uuid"],
        }

    def test_create_endpoint_any_value_omits_property_value_ids(self) -> None:
        # BE OpenAPI schema declares ``property_value_ids`` as a non-nullable
        # array; sending ``null`` fails schema validation. Omitting the key
        # is the documented shape for ``any_value`` triggers.
        prop = _make_property(
            name="child",
            parent_name="Parent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        prop.parent_property_id = "parent-uuid"
        body = prop.to_create_endpoint()
        assert body["trigger_condition"] == {"type": "any_value"}
        assert "property_value_ids" not in body["trigger_condition"]

    def test_create_endpoint_rejects_unresolved_parent(self) -> None:
        # ``parent_name`` without ``parent_property_id`` means the importer
        # hasn't resolved the name against the server yet — sending it as-is
        # would lose the nesting silently.
        prop = _make_property(
            name="child",
            parent_name="Parent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(ValueError):
            prop.to_create_endpoint()

    def test_create_endpoint_rejects_parent_without_trigger(self) -> None:
        prop = _make_property(name="child")
        prop.parent_property_id = "parent-uuid"
        with pytest.raises(ValueError):
            prop.to_create_endpoint()

    def test_update_endpoint_excludes_immutable_nesting_fields(self) -> None:
        prop = _make_property(
            id_="3",
            name="child",
            trigger_condition=TriggerCondition(type="any_value"),
            parent_name="Parent",
        )
        prop.parent_property_id = "parent-uuid"
        _, body = prop.to_update_endpoint()
        assert "parent_property_id" not in body
        assert "trigger_condition" not in body
        assert "granularity" not in body


class TestTopologicalSort:
    def test_empty_returns_empty(self) -> None:
        assert _topologically_sort_properties_to_create([]) == []

    def test_parent_always_precedes_child(self) -> None:
        parent = _make_property(name="parent")
        child = _make_property(
            name="child",
            parent_name="parent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        ordered = _topologically_sort_properties_to_create([child, parent])
        assert [p.name for p in ordered] == ["parent", "child"]

    def test_deep_chain_is_ordered(self) -> None:
        root = _make_property(name="root")
        mid = _make_property(
            name="mid",
            parent_name="root",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        leaf = _make_property(
            name="leaf",
            parent_name="mid",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        ordered = _topologically_sort_properties_to_create([leaf, mid, root])
        assert [p.name for p in ordered] == ["root", "mid", "leaf"]

    def test_siblings_preserve_input_order(self) -> None:
        root = _make_property(name="root")
        a = _make_property(
            name="a",
            parent_name="root",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        b = _make_property(
            name="b",
            parent_name="root",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        ordered = _topologically_sort_properties_to_create([a, b, root])
        assert [p.name for p in ordered] == ["root", "a", "b"]

    def test_unknown_parent_treated_as_root(self) -> None:
        orphan = _make_property(
            name="orphan",
            parent_name="unknown",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        ordered = _topologically_sort_properties_to_create([orphan])
        assert [p.name for p in ordered] == ["orphan"]

    def test_cycle_raises(self) -> None:
        a = _make_property(
            name="a",
            parent_name="b",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        b = _make_property(
            name="b",
            parent_name="a",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(ValueError):
            _topologically_sort_properties_to_create([a, b])

    def test_item_level_and_class_level_do_not_interleave(self) -> None:
        # A class-level property named "Shared" and an item-level property
        # with the same name should not be treated as the same node.
        class_level = _make_property(name="Shared")
        item_level = _make_property(
            name="Shared",
            annotation_class_id=None,
            granularity=PropertyGranularity.item,
        )
        ordered = _topologically_sort_properties_to_create([class_level, item_level])
        assert ordered == [class_level, item_level]


class TestEnrichWithMetadataValues:
    def test_appends_missing_metadata_values_for_class_level_property(self) -> None:
        prop = _make_property(
            name="Defect Type",
            type_="multi_select",
            property_values=[PropertyValue(value="Contamination")],
        )
        metadata_cls_prop_lookup = {
            ("test_class", "Defect Type"): dt.Property(
                name="Defect Type",
                type="multi_select",
                required=False,
                property_values=[
                    {"value": "Contamination"},
                    {"value": "Scratch"},
                ],
                granularity=PropertyGranularity.annotation,
            )
        }
        _enrich_properties_with_metadata_values(
            [prop],
            metadata_cls_prop_lookup=metadata_cls_prop_lookup,
            metadata_item_prop_lookup={},
            annotation_class_ids_map={("test_class", "polygon"): "1"},
        )
        values = {pv.value for pv in prop.property_values}
        assert values == {"Contamination", "Scratch"}

    def test_no_op_when_metadata_missing(self) -> None:
        prop = _make_property(
            name="Defect Type",
            type_="multi_select",
            property_values=[PropertyValue(value="x")],
        )
        _enrich_properties_with_metadata_values(
            [prop],
            metadata_cls_prop_lookup={},
            metadata_item_prop_lookup={},
            annotation_class_ids_map={("test_class", "polygon"): "1"},
        )
        assert [pv.value for pv in prop.property_values] == ["x"]


def _fake_team_property_lookups(
    annotation_properties=None, item_properties=None
) -> TeamPropertyLookups:
    lookups = TeamPropertyLookups.__new__(TeamPropertyLookups)
    lookups.annotation_properties = annotation_properties or {}
    lookups.item_properties = item_properties or {}
    lookups._client = Mock()  # type: ignore[attr-defined]
    lookups._team_slug = "test_team"  # type: ignore[attr-defined]
    return lookups


class TestResolveParentForCreate:
    def test_returns_as_is_for_top_level(self) -> None:
        prop = _make_property(name="top")
        resolved = _resolve_parent_for_create(prop, _fake_team_property_lookups())
        assert resolved is prop

    def test_resolves_class_level_parent_name_and_trigger_values(self) -> None:
        parent_on_server = FullProperty(
            id="new-parent-id",
            name="Defect Type",
            type="multi_select",
            required=False,
            annotation_class_id=1,
            property_values=[
                PropertyValue(id="new-cont-id", value="Contamination"),
                PropertyValue(id="new-scratch-id", value="Scratch"),
            ],
            granularity=PropertyGranularity.annotation,
        )
        lookups = _fake_team_property_lookups(
            annotation_properties={("Defect Type", 1): parent_on_server}
        )
        child = _make_property(
            name="Contamination Source",
            parent_name="Defect Type",
            trigger_condition=TriggerCondition(
                type="value_match", values=["Contamination"]
            ),
        )
        resolved = _resolve_parent_for_create(child, lookups)
        assert resolved.parent_property_id == "new-parent-id"
        assert resolved.trigger_condition is not None
        assert resolved.trigger_condition.property_value_ids == ["new-cont-id"]
        # The original (name-based) ``trigger_condition.values`` is dropped
        # from the API-ready copy to avoid double-encoding.
        assert resolved.trigger_condition.values is None

    def test_resolves_any_value_trigger(self) -> None:
        parent_on_server = FullProperty(
            id="notes-id",
            name="Notes",
            type="text",
            required=False,
            annotation_class_id=1,
            granularity=PropertyGranularity.annotation,
        )
        lookups = _fake_team_property_lookups(
            annotation_properties={("Notes", 1): parent_on_server}
        )
        child = _make_property(
            name="Translation Required?",
            parent_name="Notes",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        resolved = _resolve_parent_for_create(child, lookups)
        assert resolved.parent_property_id == "notes-id"
        assert resolved.trigger_condition is not None
        assert resolved.trigger_condition.type == "any_value"
        assert resolved.trigger_condition.property_value_ids is None

    def test_resolves_item_level_parent(self) -> None:
        parent_on_server = FullProperty(
            id="item-parent-id",
            name="item_level_parent",
            type="text",
            required=False,
            granularity=PropertyGranularity.item,
        )
        lookups = _fake_team_property_lookups(
            item_properties={"item_level_parent": parent_on_server}
        )
        child = FullProperty(
            name="item_level_child",
            type="single_select",
            required=False,
            granularity=PropertyGranularity.item,
            property_values=[PropertyValue(value="Yes")],
            slug="team-slug",
            parent_name="item_level_parent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        resolved = _resolve_parent_for_create(child, lookups)
        assert resolved.parent_property_id == "item-parent-id"

    def test_missing_parent_raises(self) -> None:
        child = _make_property(
            name="child",
            parent_name="Nonexistent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(ValueError, match="Cannot resolve parent"):
            _resolve_parent_for_create(child, _fake_team_property_lookups())

    def test_unknown_trigger_value_raises(self) -> None:
        parent_on_server = FullProperty(
            id="p-id",
            name="Parent",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="v-id", value="KnownValue")],
            granularity=PropertyGranularity.annotation,
        )
        lookups = _fake_team_property_lookups(
            annotation_properties={("Parent", 1): parent_on_server}
        )
        child = _make_property(
            name="child",
            parent_name="Parent",
            trigger_condition=TriggerCondition(
                type="value_match", values=["UnknownValue"]
            ),
        )
        with pytest.raises(ValueError, match="unknown parent value"):
            _resolve_parent_for_create(child, lookups)


class TestGetVisibleProperties:
    def _parent(self) -> FullProperty:
        return FullProperty(
            id="parent-id",
            name="Finding Type",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[
                PropertyValue(id="frac-id", value="Fracture"),
                PropertyValue(id="norm-id", value="Normal"),
            ],
            granularity=PropertyGranularity.annotation,
        )

    def _value_match_child_by_name(self) -> FullProperty:
        return FullProperty(
            id="child-id",
            name="Bone",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="femur-id", value="Femur")],
            granularity=PropertyGranularity.annotation,
            parent_name="Finding Type",
            trigger_condition=TriggerCondition(type="value_match", values=["Fracture"]),
        )

    def test_top_level_always_visible(self) -> None:
        parent = self._parent()
        selected = [SelectedProperty(name="Finding Type", value="Fracture")]
        assert get_visible_properties(selected, [parent]) == selected

    def test_value_match_child_visible_when_parent_matches(self) -> None:
        parent = self._parent()
        child = self._value_match_child_by_name()
        selected = [
            SelectedProperty(name="Finding Type", value="Fracture"),
            SelectedProperty(name="Bone", value="Femur"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Finding Type", "Bone"]

    def test_value_match_child_hidden_when_parent_does_not_match(self) -> None:
        parent = self._parent()
        child = self._value_match_child_by_name()
        selected = [
            SelectedProperty(name="Finding Type", value="Normal"),
            SelectedProperty(name="Bone", value="Femur"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Finding Type"]

    def test_value_match_child_hidden_when_parent_empty(self) -> None:
        parent = self._parent()
        child = self._value_match_child_by_name()
        selected = [SelectedProperty(name="Bone", value="Femur")]
        visible = get_visible_properties(selected, [parent, child])
        assert visible == []

    def test_value_match_via_property_value_ids_still_supported(self) -> None:
        # API responses may carry UUIDs only; the visibility engine still
        # resolves them against the parent's ``property_values`` so consumers
        # who feed raw API payloads into ``get_visible_properties`` are not
        # forced to rewrite them into name-based shape first.
        parent = self._parent()
        child = FullProperty(
            id="child-id",
            name="Bone",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="femur-id", value="Femur")],
            granularity=PropertyGranularity.annotation,
            parent_property_id="parent-id",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["frac-id"]
            ),
        )
        selected = [
            SelectedProperty(name="Finding Type", value="Fracture"),
            SelectedProperty(name="Bone", value="Femur"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Finding Type", "Bone"]

    def test_any_value_child_visible_when_parent_has_text(self) -> None:
        parent = FullProperty(
            id="notes-id",
            name="Notes",
            type="text",
            required=False,
            annotation_class_id=1,
            granularity=PropertyGranularity.annotation,
        )
        child = FullProperty(
            id="trans-id",
            name="Translation Required?",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="yes-id", value="Yes")],
            granularity=PropertyGranularity.annotation,
            parent_name="Notes",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [
            SelectedProperty(name="Notes", value="something"),
            SelectedProperty(name="Translation Required?", value="Yes"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Notes", "Translation Required?"]

    def test_any_value_child_hidden_when_parent_text_is_whitespace(self) -> None:
        parent = FullProperty(
            id="notes-id",
            name="Notes",
            type="text",
            required=False,
            annotation_class_id=1,
            granularity=PropertyGranularity.annotation,
        )
        child = FullProperty(
            id="trans-id",
            name="Translation Required?",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="yes-id", value="Yes")],
            granularity=PropertyGranularity.annotation,
            parent_name="Notes",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [
            SelectedProperty(name="Notes", value="   "),
            SelectedProperty(name="Translation Required?", value="Yes"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Notes"]

    def test_grandchild_hidden_when_grandparent_hidden(self) -> None:
        grand = self._parent()
        parent = FullProperty(
            id="mid-id",
            name="Bone",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="femur-id", value="Femur")],
            granularity=PropertyGranularity.annotation,
            parent_name="Finding Type",
            trigger_condition=TriggerCondition(type="value_match", values=["Fracture"]),
        )
        grandchild = FullProperty(
            id="grand-id",
            name="Severity",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="mild-id", value="Mild")],
            granularity=PropertyGranularity.annotation,
            parent_name="Bone",
            trigger_condition=TriggerCondition(type="value_match", values=["Femur"]),
        )
        selected = [
            SelectedProperty(name="Finding Type", value="Normal"),
            SelectedProperty(name="Bone", value="Femur"),
            SelectedProperty(name="Severity", value="Mild"),
        ]
        visible = get_visible_properties(selected, [grand, parent, grandchild])
        assert [s.name for s in visible] == ["Finding Type"]

    def test_multi_select_parent_visible_when_one_value_matches(self) -> None:
        parent = FullProperty(
            id="defect-id",
            name="Defect Type",
            type="multi_select",
            required=False,
            annotation_class_id=1,
            property_values=[
                PropertyValue(id="cont-id", value="Contamination"),
                PropertyValue(id="scratch-id", value="Scratch"),
            ],
            granularity=PropertyGranularity.annotation,
        )
        child = FullProperty(
            id="src-id",
            name="Contamination Source",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="chem-id", value="Chemical")],
            granularity=PropertyGranularity.annotation,
            parent_name="Defect Type",
            trigger_condition=TriggerCondition(
                type="value_match", values=["Contamination"]
            ),
        )
        selected = [
            SelectedProperty(name="Defect Type", value="Scratch"),
            SelectedProperty(name="Defect Type", value="Contamination"),
            SelectedProperty(name="Contamination Source", value="Chemical"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == [
            "Defect Type",
            "Defect Type",
            "Contamination Source",
        ]

    def test_missing_definition_is_passed_through(self) -> None:
        selected = [SelectedProperty(name="Unknown", value="x")]
        assert get_visible_properties(selected, []) == selected

    def test_cycle_in_parent_references_does_not_recurse_forever(self) -> None:
        a = FullProperty(
            id="a-id",
            name="A",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="a-val", value="a")],
            granularity=PropertyGranularity.annotation,
            parent_name="B",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        b = FullProperty(
            id="b-id",
            name="B",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="b-val", value="b")],
            granularity=PropertyGranularity.annotation,
            parent_name="A",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [
            SelectedProperty(name="A", value="a"),
            SelectedProperty(name="B", value="b"),
        ]
        # Must return without raising.
        assert get_visible_properties(selected, [a, b]) == []

    def test_same_name_across_scopes_does_not_collide_in_cache(self) -> None:
        # Regression for the ``get_visible_properties`` name-collision bug:
        # an item-level and a class-level property may legitimately share a
        # name. They must not share a cache slot or shadow each other in the
        # definition lookup used for nesting resolution.
        item_level = FullProperty(
            id="item-status-id",
            name="Status",
            type="text",
            required=False,
            annotation_class_id=None,
            granularity=PropertyGranularity.item,
        )
        class_level_parent = FullProperty(
            id="class-status-id",
            name="Status",
            type="single_select",
            required=False,
            annotation_class_id=42,
            property_values=[PropertyValue(id="open-id", value="Open")],
            granularity=PropertyGranularity.annotation,
        )
        class_level_child = FullProperty(
            id="class-child-id",
            name="Reason",
            type="text",
            required=False,
            annotation_class_id=42,
            granularity=PropertyGranularity.annotation,
            parent_name="Status",
            trigger_condition=TriggerCondition(type="value_match", values=["Open"]),
        )
        # The class-level parent DOES have a triggering value, so the child
        # must be visible. The item-level "Status" is empty but must not
        # poison the visibility decision for the class-level tree.
        selected = [
            SelectedProperty(name="Status", value="Open"),
            SelectedProperty(name="Reason", value="Late"),
        ]
        visible = get_visible_properties(
            selected, [item_level, class_level_parent, class_level_child]
        )
        assert [s.name for s in visible] == ["Status", "Reason"]

    def test_any_value_child_hidden_when_parent_has_no_selection(self) -> None:
        parent = FullProperty(
            id="defect-id",
            name="Defect Type",
            type="multi_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="cont-id", value="Contamination")],
            granularity=PropertyGranularity.annotation,
        )
        child = FullProperty(
            id="src-id",
            name="Contamination Source",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="chem-id", value="Chemical")],
            granularity=PropertyGranularity.annotation,
            parent_name="Defect Type",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [SelectedProperty(name="Contamination Source", value="Chemical")]
        visible = get_visible_properties(selected, [parent, child])
        assert visible == []


class TestMetadataParsing:
    def _nested_metadata(self) -> dict:
        return {
            "classes": [
                {
                    "name": "defect",
                    "type": "bounding_box",
                    "description": None,
                    "properties": [
                        {
                            "name": "Defect Type",
                            "type": "multi_select",
                            "required": False,
                            "granularity": "annotation",
                            "property_values": [
                                {"value": "Contamination"},
                                {"value": "Scratch"},
                            ],
                        },
                        {
                            "name": "Contamination Source",
                            "type": "single_select",
                            "required": True,
                            "granularity": "annotation",
                            "property_values": [{"value": "Chemical"}],
                            "parent_name": "Defect Type",
                            "trigger_condition": {
                                "type": "value_match",
                                "values": ["Contamination"],
                            },
                        },
                    ],
                }
            ]
        }

    def test_parse_property_classes_preserves_nesting_fields(self) -> None:
        classes = parse_property_classes(self._nested_metadata())
        assert len(classes) == 1
        parent, child = classes[0].properties

        assert parent.parent_name is None
        assert parent.trigger_condition is None

        assert child.parent_name == "Defect Type"
        assert child.trigger_condition is not None
        assert child.trigger_condition.type == "value_match"
        assert child.trigger_condition.values == ["Contamination"]

    def test_metadataclass_parses_nested_properties(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            metadata_path = Path(tmp) / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(self._nested_metadata(), f)
            parsed = MetaDataClass.from_path(metadata_path)

        parent_def, child_def = parsed[0].properties
        assert parent_def.parent_name is None
        assert child_def.parent_name == "Defect Type"
        assert child_def.trigger_condition is not None
        assert child_def.trigger_condition.type == "value_match"
        assert child_def.trigger_condition.values == ["Contamination"]

    def test_parse_property_classes_tolerates_missing_nesting_fields(self) -> None:
        legacy = {
            "classes": [
                {
                    "name": "legacy",
                    "type": "polygon",
                    "description": None,
                    "properties": [
                        {
                            "name": "Flat Prop",
                            "type": "text",
                            "required": False,
                            "granularity": "section",
                            "property_values": [],
                        }
                    ],
                }
            ]
        }
        classes = parse_property_classes(legacy)
        prop = classes[0].properties[0]
        assert prop.parent_name is None
        assert prop.trigger_condition is None


class TestE2EFixture:
    """
    Smoke-tests that the E2E fixture
    ``e2e_tests/data/import/image_annotations_with_nested_properties`` is
    well-formed: every child references a parent by name that exists and
    every ``value_match`` trigger names a value that exists on the parent.
    """

    def _fixture_root(self) -> Path:
        return (
            Path(__file__).resolve().parents[4]
            / "e2e_tests"
            / "data"
            / "import"
            / "image_annotations_with_nested_properties"
        )

    def test_metadata_fixture_is_self_consistent(self) -> None:
        fixture = self._fixture_root() / ".v7" / "metadata.json"
        assert fixture.is_file(), f"fixture missing: {fixture}"

        with open(fixture) as f:
            raw = json.load(f)
        classes = parse_property_classes(raw)

        class_level_granularities = {
            prop.granularity.value
            for klass in classes
            for prop in (klass.properties or [])
        }
        assert "annotation" in class_level_granularities
        assert "section" in class_level_granularities

        item_granularities = {p["granularity"] for p in raw["properties"]}
        assert item_granularities == {"item"}

        # Class-level parent resolution by name.
        for klass in classes:
            by_name = {p.name: p for p in klass.properties or []}
            children = [p for p in by_name.values() if p.parent_name is not None]
            assert children, f"class '{klass.name}' has no nested children"
            for child in children:
                parent = by_name.get(child.parent_name)
                assert parent is not None, (
                    f"child '{child.name}' references missing parent "
                    f"'{child.parent_name}' in class '{klass.name}'"
                )
                trigger = child.trigger_condition
                assert trigger is not None
                if trigger.type == "value_match":
                    parent_value_names = {
                        pv.get("value") for pv in (parent.property_values or [])
                    }
                    assert set(trigger.values or []).issubset(parent_value_names), (
                        f"child '{child.name}' value_match references an "
                        f"unknown parent value"
                    )

        # Item-level parent resolution by name.
        item_props_by_name = {p["name"]: p for p in raw["properties"]}
        item_children = [p for p in item_props_by_name.values() if p.get("parent_name")]
        assert item_children, "item-level fixture must include nested children"
        for child in item_children:
            assert child["parent_name"] in item_props_by_name

    def test_annotation_fixture_references_known_properties(self) -> None:
        fixture_root = self._fixture_root()
        metadata = json.loads((fixture_root / ".v7" / "metadata.json").read_text())
        class_prop_names = {
            p["name"] for k in metadata["classes"] for p in k["properties"]
        }
        item_prop_names = {p["name"] for p in metadata["properties"]}

        annotation_file = json.loads((fixture_root / "image_1.json").read_text())
        for annotation in annotation_file["annotations"]:
            for selected in annotation.get("properties", []):
                assert selected["name"] in class_prop_names
        for selected in annotation_file.get("properties", []):
            assert selected["name"] in item_prop_names


class TestImportPropertiesNestedIntegration:
    """
    Exercises ``_import_properties`` end-to-end with a nested hierarchy and
    a mocked client.
    """

    @pytest.fixture
    def mock_dataset(self) -> Mock:
        dataset = Mock()
        dataset.team = "test_team"
        dataset.name = "test_dataset"
        dataset.dataset_id = 1
        return dataset

    def _metadata_with_child_listed_before_parent(self) -> dict:
        return {
            "classes": [
                {
                    "name": "test_class",
                    "type": "polygon",
                    "description": None,
                    "properties": [
                        # Child intentionally first in metadata order.
                        {
                            "name": "Contamination Source",
                            "type": "single_select",
                            "required": False,
                            "granularity": "annotation",
                            "property_values": [{"value": "Chemical"}],
                            "parent_name": "Defect Type",
                            "trigger_condition": {
                                "type": "value_match",
                                "values": ["Contamination"],
                            },
                        },
                        {
                            "name": "Defect Type",
                            "type": "multi_select",
                            "required": False,
                            "granularity": "annotation",
                            "property_values": [{"value": "Contamination"}],
                        },
                    ],
                }
            ]
        }

    def test_creates_parent_before_child_and_resolves_names_to_uuids(
        self, mock_dataset: Mock
    ) -> None:
        client = Mock()
        client.default_team = "test_team"
        annotation_class_ids_map = {("test_class", "polygon"): "123"}
        annotations = [
            dt.Annotation(
                dt.AnnotationClass("test_class", "polygon"),
                {"paths": [[1, 2, 3, 4, 5]]},
                [],
                [],
                id="annotation_id_1",
                properties=[
                    SelectedProperty(
                        frame_index=None,
                        name="Defect Type",
                        type="multi_select",
                        value="Contamination",
                    ),
                    SelectedProperty(
                        frame_index=None,
                        name="Contamination Source",
                        type="single_select",
                        value="Chemical",
                    ),
                ],
            )
        ]

        mock_lookups = Mock()
        mock_lookups.annotation_properties = {}
        mock_lookups.item_properties = {}
        created_server_properties: List[FullProperty] = []

        def refresh():
            for prop in created_server_properties:
                if prop.granularity.value in ("section", "annotation"):
                    mock_lookups.annotation_properties[(prop.name, 123)] = prop
                else:
                    mock_lookups.item_properties[prop.name] = prop

        mock_lookups.refresh = refresh

        created_payloads: List[FullProperty] = []

        def fake_create_property(
            *, team_slug: str, params: FullProperty
        ) -> FullProperty:
            created_payloads.append(params)
            server_prop = params.model_copy()
            server_prop.id = f"new-{params.name.lower().replace(' ', '-')}"
            server_prop.property_values = [
                PropertyValue(
                    id=f"new-val-{pv.value.lower()}",
                    value=pv.value,
                    color=pv.color,
                )
                for pv in (params.property_values or [])
            ]
            created_server_properties.append(server_prop)
            return server_prop

        client.create_property.side_effect = fake_create_property
        client.update_property = Mock()
        client.get_team_properties = Mock(return_value=[])

        with tempfile.TemporaryDirectory() as tmp:
            metadata_path = Path(tmp) / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(self._metadata_with_child_listed_before_parent(), f)

            _import_properties(
                metadata_path,
                [],
                client,
                annotations,
                annotation_class_ids_map,
                mock_dataset,
                annotation_id_property_map={},
                team_property_lookups=mock_lookups,
            )

        assert len(created_payloads) == 2

        # Parent first (topological sort applied).
        assert created_payloads[0].name == "Defect Type"
        assert created_payloads[0].parent_property_id is None
        assert created_payloads[0].trigger_condition is None

        # Child second, with the parent's freshly-assigned server UUID and
        # trigger-value UUIDs resolved from its ``values`` (names).
        assert created_payloads[1].name == "Contamination Source"
        assert created_payloads[1].parent_property_id == "new-defect-type"
        assert created_payloads[1].trigger_condition is not None
        assert created_payloads[1].trigger_condition.type == "value_match"
        assert created_payloads[1].trigger_condition.property_value_ids == [
            "new-val-contamination"
        ]
