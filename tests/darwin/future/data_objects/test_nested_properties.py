"""Unit tests for nested-property SDK support (parent_property_id, trigger_condition,
topological sort, and visibility filtering).
"""

import json
import tempfile
from pathlib import Path
from typing import List, Optional
from unittest.mock import Mock

import pytest

import darwin.datatypes as dt
from darwin.datatypes import parse_property_classes
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
    _remap_property_for_create,
    _topologically_sort_properties_to_create,
)


def _make_property(
    *,
    id_: str,
    name: str,
    type_: str = "single_select",
    property_values: Optional[List[PropertyValue]] = None,
    parent_property_id: Optional[str] = None,
    trigger_condition: Optional[TriggerCondition] = None,
) -> FullProperty:
    return FullProperty(
        id=id_,
        name=name,
        type=type_,
        required=False,
        annotation_class_id=1,
        slug="team-slug",
        property_values=property_values or [],
        granularity=PropertyGranularity.annotation,
        parent_property_id=parent_property_id,
        trigger_condition=trigger_condition,
    )


class TestTriggerCondition:
    def test_value_match_requires_ids(self) -> None:
        with pytest.raises(ValueError):
            TriggerCondition(type="value_match", property_value_ids=[])

    def test_value_match_rejects_none_ids(self) -> None:
        with pytest.raises(ValueError):
            TriggerCondition(type="value_match")

    def test_value_match_accepts_ids(self) -> None:
        cond = TriggerCondition(type="value_match", property_value_ids=["abc"])
        assert cond.property_value_ids == ["abc"]

    def test_any_value_does_not_require_ids(self) -> None:
        cond = TriggerCondition(type="any_value")
        assert cond.property_value_ids is None

    def test_any_value_rejects_non_empty_ids(self) -> None:
        # TDD 14.2 / line 988: any_value + property_value_ids must be rejected.
        with pytest.raises(ValueError):
            TriggerCondition(type="any_value", property_value_ids=["abc"])

    def test_any_value_accepts_empty_ids_list(self) -> None:
        # Empty list is semantically equivalent to None — must be accepted.
        cond = TriggerCondition(type="any_value", property_value_ids=[])
        assert not cond.property_value_ids

    def test_rejects_unknown_type(self) -> None:
        # TDD 14.2: trigger_condition.type unknown string must be invalid.
        with pytest.raises(Exception):  # pydantic ValidationError
            TriggerCondition(type="bogus_type")  # type: ignore[arg-type]


class TestFullPropertyEndpoints:
    def test_create_endpoint_omits_nesting_when_absent(self) -> None:
        prop = _make_property(id_="1", name="top")
        body = prop.to_create_endpoint()
        assert "parent_property_id" not in body
        assert "trigger_condition" not in body

    def test_create_endpoint_includes_nesting_when_present(self) -> None:
        prop = _make_property(
            id_="2",
            name="child",
            parent_property_id="parent-id",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["val-id"]
            ),
        )
        body = prop.to_create_endpoint()
        assert body["parent_property_id"] == "parent-id"
        assert body["trigger_condition"] == {
            "type": "value_match",
            "property_value_ids": ["val-id"],
        }

    def test_update_endpoint_excludes_immutable_nesting_fields(self) -> None:
        prop = _make_property(
            id_="3",
            name="child",
            parent_property_id="parent-id",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        _, body = prop.to_update_endpoint()
        assert "parent_property_id" not in body
        assert "trigger_condition" not in body
        assert "granularity" not in body

    def test_create_endpoint_rejects_parent_without_trigger(self) -> None:
        # TDD 14.2: parent_property_id set but trigger_condition nil -> invalid.
        prop = _make_property(
            id_="4",
            name="child",
            parent_property_id="parent-id",
            trigger_condition=None,
        )
        with pytest.raises(ValueError):
            prop.to_create_endpoint()

    def test_create_endpoint_rejects_trigger_without_parent(self) -> None:
        # TDD 14.2: trigger_condition set but parent_property_id nil -> invalid.
        prop = _make_property(
            id_="5",
            name="child",
            parent_property_id=None,
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(ValueError):
            prop.to_create_endpoint()


class TestTopologicalSort:
    def test_empty_returns_empty(self) -> None:
        assert _topologically_sort_properties_to_create([]) == []

    def test_parent_always_precedes_child(self) -> None:
        parent = _make_property(id_="p", name="parent")
        child = _make_property(
            id_="c",
            name="child",
            parent_property_id="p",
            trigger_condition=TriggerCondition(type="any_value"),
        )

        ordered = _topologically_sort_properties_to_create([child, parent])
        assert [p.id for p in ordered] == ["p", "c"]

    def test_deep_chain_is_ordered(self) -> None:
        root = _make_property(id_="r", name="root")
        mid = _make_property(
            id_="m",
            name="mid",
            parent_property_id="r",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        leaf = _make_property(
            id_="l",
            name="leaf",
            parent_property_id="m",
            trigger_condition=TriggerCondition(type="any_value"),
        )

        ordered = _topologically_sort_properties_to_create([leaf, mid, root])
        assert [p.id for p in ordered] == ["r", "m", "l"]

    def test_siblings_preserve_input_order(self) -> None:
        root = _make_property(id_="r", name="root")
        a = _make_property(
            id_="a",
            name="a",
            parent_property_id="r",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        b = _make_property(
            id_="b",
            name="b",
            parent_property_id="r",
            trigger_condition=TriggerCondition(type="any_value"),
        )

        ordered = _topologically_sort_properties_to_create([a, b, root])
        assert [p.id for p in ordered] == ["r", "a", "b"]

    def test_unknown_parent_treated_as_root(self) -> None:
        orphan = _make_property(
            id_="o",
            name="orphan",
            parent_property_id="unknown-parent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        ordered = _topologically_sort_properties_to_create([orphan])
        assert [p.id for p in ordered] == ["o"]

    def test_cycle_raises(self) -> None:
        a = _make_property(
            id_="a",
            name="a",
            parent_property_id="b",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        b = _make_property(
            id_="b",
            name="b",
            parent_property_id="a",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(ValueError):
            _topologically_sort_properties_to_create([a, b])


class TestEnrichWithMetadataValues:
    def test_appends_missing_metadata_values_for_class_level_property(self) -> None:
        from darwin.datatypes import Property as MetadataProperty

        prop = _make_property(
            id_="p",
            name="Defect Type",
            type_="multi_select",
            property_values=[
                PropertyValue(id="src-contamination-id", value="Contamination")
            ],
        )
        metadata_cls_prop_lookup = {
            ("test_class", "Defect Type"): MetadataProperty(
                name="Defect Type",
                type="multi_select",
                required=False,
                property_values=[
                    {"id": "src-contamination-id", "value": "Contamination"},
                    {"id": "src-scratch-id", "value": "Scratch"},
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
        # Preserves the source id on the newly appended value so that
        # children referencing it via trigger_condition.property_value_ids
        # can be remapped after the parent is created on the server.
        new_scratch = next(pv for pv in prop.property_values if pv.value == "Scratch")
        assert new_scratch.id == "src-scratch-id"

    def test_no_op_when_metadata_missing(self) -> None:
        prop = _make_property(
            id_="p",
            name="Defect Type",
            type_="multi_select",
            property_values=[PropertyValue(id="x", value="x")],
        )
        _enrich_properties_with_metadata_values(
            [prop],
            metadata_cls_prop_lookup={},
            metadata_item_prop_lookup={},
            annotation_class_ids_map={("test_class", "polygon"): "1"},
        )
        assert [pv.value for pv in prop.property_values] == ["x"]


class TestRemapPropertyForCreate:
    def test_remaps_parent_id(self) -> None:
        child = _make_property(
            id_="c",
            name="c",
            parent_property_id="old-p",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        remapped = _remap_property_for_create(child, {"old-p": "new-p"}, {})
        assert remapped.parent_property_id == "new-p"

    def test_remaps_value_ids(self) -> None:
        child = _make_property(
            id_="c",
            name="c",
            parent_property_id="p",
            trigger_condition=TriggerCondition(
                type="value_match",
                property_value_ids=["old-v-1", "old-v-2"],
            ),
        )
        remapped = _remap_property_for_create(
            child, {"p": "p"}, {"old-v-1": "new-v-1", "old-v-2": "new-v-2"}
        )
        assert remapped.trigger_condition.property_value_ids == [
            "new-v-1",
            "new-v-2",
        ]

    def test_leaves_unmapped_ids_untouched(self) -> None:
        child = _make_property(
            id_="c",
            name="c",
            parent_property_id="old-p",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["old-v"]
            ),
        )
        remapped = _remap_property_for_create(child, {}, {})
        assert remapped.parent_property_id == "old-p"
        assert remapped.trigger_condition.property_value_ids == ["old-v"]

    def test_no_op_when_no_nesting(self) -> None:
        top = _make_property(id_="t", name="top")
        remapped = _remap_property_for_create(top, {"anything": "other"}, {})
        assert remapped is top


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

    def _value_match_child(self) -> FullProperty:
        return FullProperty(
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

    def test_top_level_always_visible(self) -> None:
        parent = self._parent()
        selected = [SelectedProperty(name="Finding Type", value="Fracture")]
        assert get_visible_properties(selected, [parent]) == selected

    def test_value_match_child_visible_when_parent_matches(self) -> None:
        parent = self._parent()
        child = self._value_match_child()
        selected = [
            SelectedProperty(name="Finding Type", value="Fracture"),
            SelectedProperty(name="Bone", value="Femur"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Finding Type", "Bone"]

    def test_value_match_child_hidden_when_parent_does_not_match(self) -> None:
        parent = self._parent()
        child = self._value_match_child()
        selected = [
            SelectedProperty(name="Finding Type", value="Normal"),
            SelectedProperty(name="Bone", value="Femur"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        assert [s.name for s in visible] == ["Finding Type"]

    def test_value_match_child_hidden_when_parent_empty(self) -> None:
        parent = self._parent()
        child = self._value_match_child()
        selected = [SelectedProperty(name="Bone", value="Femur")]
        visible = get_visible_properties(selected, [parent, child])
        assert visible == []

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
            parent_property_id="notes-id",
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
            parent_property_id="notes-id",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [
            SelectedProperty(name="Notes", value="   "),
            SelectedProperty(name="Translation Required?", value="Yes"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        # Top-level "Notes" is visible regardless of its content; the child is
        # hidden because the parent text is whitespace-only (effectively empty).
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
            parent_property_id="parent-id",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["frac-id"]
            ),
        )
        grandchild = FullProperty(
            id="grand-id",
            name="Severity",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="mild-id", value="Mild")],
            granularity=PropertyGranularity.annotation,
            parent_property_id="mid-id",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["femur-id"]
            ),
        )
        # Grandparent not matching -> everything below hidden.
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
            parent_property_id="defect-id",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["cont-id"]
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
        # Pathological input: A's parent is B and B's parent is A. The
        # backend rejects this at create time, but the public utility must
        # fail gracefully (treat as hidden) rather than RecursionError.
        a = FullProperty(
            id="a-id",
            name="A",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="a-val", value="a")],
            granularity=PropertyGranularity.annotation,
            parent_property_id="b-id",
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
            parent_property_id="a-id",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [
            SelectedProperty(name="A", value="a"),
            SelectedProperty(name="B", value="b"),
        ]
        # Must return without raising. Both are hidden because neither has
        # a reachable root.
        assert get_visible_properties(selected, [a, b]) == []

    def test_any_value_child_hidden_when_parent_has_no_selection(self) -> None:
        parent = FullProperty(
            id="defect-id",
            name="Defect Type",
            type="multi_select",
            required=False,
            annotation_class_id=1,
            property_values=[
                PropertyValue(id="cont-id", value="Contamination"),
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
            parent_property_id="defect-id",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [SelectedProperty(name="Contamination Source", value="Chemical")]
        visible = get_visible_properties(selected, [parent, child])
        assert visible == []

    def test_any_value_child_hidden_when_parent_value_is_none(self) -> None:
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
            parent_property_id="notes-id",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        selected = [
            SelectedProperty(name="Notes", value=None),
            SelectedProperty(name="Translation Required?", value="Yes"),
        ]
        visible = get_visible_properties(selected, [parent, child])
        # Top-level "Notes" with None is still "selected" (user touched it),
        # but the child must hide because the parent effectively has no value.
        assert [s.name for s in visible] == ["Notes"]


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
                            "id": "old-parent-id",
                            "name": "Defect Type",
                            "type": "multi_select",
                            "required": False,
                            "granularity": "annotation",
                            "property_values": [
                                {"id": "old-cont-id", "value": "Contamination"},
                                {"id": "old-scratch-id", "value": "Scratch"},
                            ],
                            "parent_property_id": None,
                            "trigger_condition": None,
                        },
                        {
                            "id": "old-child-id",
                            "name": "Contamination Source",
                            "type": "single_select",
                            "required": True,
                            "granularity": "annotation",
                            "property_values": [
                                {"id": "old-chem-id", "value": "Chemical"},
                            ],
                            "parent_property_id": "old-parent-id",
                            "trigger_condition": {
                                "type": "value_match",
                                "property_value_ids": ["old-cont-id"],
                            },
                        },
                    ],
                }
            ]
        }

    def test_parse_property_classes_preserves_nesting_fields(self) -> None:
        classes = parse_property_classes(self._nested_metadata())
        assert len(classes) == 1
        props = classes[0].properties
        assert props is not None
        parent, child = props

        assert parent.id == "old-parent-id"
        assert parent.parent_property_id is None
        assert parent.trigger_condition is None

        assert child.id == "old-child-id"
        assert child.parent_property_id == "old-parent-id"
        assert child.trigger_condition is not None
        assert child.trigger_condition.type == "value_match"
        assert child.trigger_condition.property_value_ids == ["old-cont-id"]

    def test_metadataclass_parses_nested_properties(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            metadata_path = Path(tmp) / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(self._nested_metadata(), f)

            parsed = MetaDataClass.from_path(metadata_path)

        assert len(parsed) == 1
        parent_def, child_def = parsed[0].properties
        assert parent_def.parent_property_id is None
        assert child_def.parent_property_id == "old-parent-id"
        assert child_def.trigger_condition is not None
        assert child_def.trigger_condition.type == "value_match"
        assert child_def.trigger_condition.property_value_ids == ["old-cont-id"]

    def test_parse_property_classes_tolerates_missing_nesting_fields(self) -> None:
        # Legacy metadata without nesting fields must still parse as top-level.
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
        assert prop.parent_property_id is None
        assert prop.trigger_condition is None
        assert prop.id is None


class TestE2EFixture:
    """
    Smoke-tests that the E2E fixture
    ``e2e_tests/data/import/image_annotations_with_nested_properties`` is
    well-formed: every child references a parent that exists, and every
    value_match trigger references a value that exists on the parent. This
    keeps the fixture honest without requiring the live E2E backend.
    """

    def _fixture_root(self) -> "Path":
        from pathlib import Path

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

        metadata = MetaDataClass.from_path(fixture)
        classes = parse_property_classes(json.loads(fixture.read_text()))

        # Spans all three granularities per the TDD PRD requirement.
        class_level_granularities = {
            prop.granularity.value
            for klass in classes
            for prop in (klass.properties or [])
        }
        assert "annotation" in class_level_granularities
        assert "section" in class_level_granularities

        with open(fixture) as f:
            raw = json.load(f)
        item_level_granularities = {p["granularity"] for p in raw["properties"]}
        assert item_level_granularities == {"item"}

        # Every child points to an existing parent id and every value_match
        # trigger references at least one value present on the parent.
        all_props = [prop for klass in classes for prop in (klass.properties or [])] + [
            parse_property_classes(
                {"classes": [{"name": "__item__", "type": "item", "properties": [p]}]}
            )[0].properties[0]
            for p in raw["properties"]
        ]
        by_id = {p.id: p for p in all_props if p.id}
        children = [p for p in all_props if p.parent_property_id is not None]
        assert children, "fixture must declare at least one nested child"
        for child in children:
            parent = by_id.get(child.parent_property_id)
            assert parent is not None, (
                f"child '{child.name}' references missing parent "
                f"{child.parent_property_id}"
            )
            trigger = child.trigger_condition
            assert trigger is not None
            if trigger.type == "value_match":
                parent_value_ids = {
                    pv.get("id")
                    for pv in (parent.property_values or [])
                    if pv.get("id")
                }
                assert set(trigger.property_value_ids or []).issubset(
                    parent_value_ids
                ), (
                    f"child '{child.name}' value_match references unknown "
                    f"parent value id"
                )

        # MetaDataClass.from_path must also succeed and surface the nesting.
        nested_children = [
            p
            for klass in metadata
            for p in klass.properties
            if p.parent_property_id is not None
        ]
        assert nested_children, "MetaDataClass did not preserve nested children"

    def test_annotation_fixture_references_known_properties(self) -> None:
        # Every per-annotation and per-item property value names a property
        # declared in the metadata fixture — the E2E round-trip otherwise
        # cannot possibly succeed.
        import json as _json

        fixture_root = self._fixture_root()
        metadata = _json.loads((fixture_root / ".v7" / "metadata.json").read_text())
        class_prop_names = {
            p["name"] for k in metadata["classes"] for p in k["properties"]
        }
        item_prop_names = {p["name"] for p in metadata["properties"]}

        annotation_file = _json.loads((fixture_root / "image_1.json").read_text())
        for annotation in annotation_file["annotations"]:
            for selected in annotation.get("properties", []):
                assert selected["name"] in class_prop_names, (
                    f"annotation references unknown class property "
                    f"'{selected['name']}'"
                )
        for selected in annotation_file.get("properties", []):
            assert (
                selected["name"] in item_prop_names
            ), f"item references unknown item property '{selected['name']}'"


class TestImportPropertiesNestedIntegration:
    """
    End-to-end coverage for ``_import_properties`` with a nested hierarchy.

    These tests exercise the real importer function with a mocked client to
    validate TDD section 12 "Import Format (Flat with Parent Reference)":
    topological ordering, parent_property_id remapping, and
    trigger_condition.property_value_ids remapping.
    """

    @pytest.fixture
    def mock_dataset(self) -> Mock:
        dataset = Mock()
        dataset.team = "test_team"
        dataset.name = "test_dataset"
        dataset.dataset_id = 1
        return dataset

    def _metadata_with_child_listed_before_parent(self) -> dict:
        # Intentionally child-first to exercise topological sorting.
        return {
            "classes": [
                {
                    "name": "test_class",
                    "type": "polygon",
                    "description": None,
                    "properties": [
                        {
                            "id": "old-child-id",
                            "name": "Contamination Source",
                            "type": "single_select",
                            "required": False,
                            "granularity": "annotation",
                            "property_values": [
                                {"id": "old-chem-id", "value": "Chemical"},
                            ],
                            "parent_property_id": "old-parent-id",
                            "trigger_condition": {
                                "type": "value_match",
                                "property_value_ids": ["old-cont-id"],
                            },
                        },
                        {
                            "id": "old-parent-id",
                            "name": "Defect Type",
                            "type": "multi_select",
                            "required": False,
                            "granularity": "annotation",
                            "property_values": [
                                {"id": "old-cont-id", "value": "Contamination"},
                            ],
                            "parent_property_id": None,
                            "trigger_condition": None,
                        },
                    ],
                }
            ]
        }

    def test_creates_parent_before_child_and_remaps_ids(
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

        # Mock the team lookups: nothing exists yet, both properties must be
        # created and the child must follow the parent.
        mock_lookups = Mock()
        mock_lookups.annotation_properties = {}
        mock_lookups.item_properties = {}

        def refresh():
            # After creation the child should be resolvable by name.
            for prop in created_server_properties:
                if prop.granularity.value in ("section", "annotation"):
                    mock_lookups.annotation_properties[(prop.name, 123)] = prop
                else:
                    mock_lookups.item_properties[prop.name] = prop

        mock_lookups.refresh = refresh

        created_payloads: List[FullProperty] = []
        created_server_properties: List[FullProperty] = []

        def fake_create_property(
            *, team_slug: str, params: FullProperty
        ) -> FullProperty:
            assert isinstance(params, FullProperty)
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

        # Parent is created first even though metadata lists it last.
        assert created_payloads[0].name == "Defect Type"
        assert created_payloads[0].parent_property_id is None
        assert created_payloads[0].trigger_condition is None

        # Child is created second with both IDs translated to the destination
        # team's IDs (returned by the mocked server).
        assert created_payloads[1].name == "Contamination Source"
        assert created_payloads[1].parent_property_id == "new-defect-type"
        assert created_payloads[1].trigger_condition is not None
        assert created_payloads[1].trigger_condition.type == "value_match"
        assert created_payloads[1].trigger_condition.property_value_ids == [
            "new-val-contamination"
        ]
