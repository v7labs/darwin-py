"""Unit tests for the nested-property SDK foundation: ``TriggerCondition``,
``FullProperty`` create/update endpoints with nesting fields,
``property_key`` helper, ``_property_value_from_metadata`` helper, the
class-level branch of ``_resolve_parent_property_for_create``, and metadata parsing
of nested fields.
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
    TriggerCondition,
    property_key,
)
from darwin.importer.importer import (
    _import_properties,
    _property_value_from_metadata,
    _resolve_parent_property_for_create,
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
        # UUIDs (via ``_resolve_parent_property_for_create``) before serialising.
        trigger = TriggerCondition(
            type="value_match",
            values=["Fracture"],
            property_value_ids=["v-1"],
        )
        assert "values" not in trigger.to_api_payload()

    def test_to_api_payload_value_match_raises_without_property_value_ids(
        self,
    ) -> None:
        # Names-only (pre-resolution) ``value_match`` trigger. Serialising
        # this would yield ``{"type": "value_match"}`` which the BE rejects
        # with an opaque 422. ``to_api_payload`` raises a clear client-side
        # error instead.
        trigger = TriggerCondition(type="value_match", values=["Fracture"])
        with pytest.raises(ValueError, match="property_value_ids"):
            trigger.to_api_payload()


class TestPropertyKey:
    def test_class_level_uses_class_id(self) -> None:
        prop = FullProperty(
            name="Status",
            type="single_select",
            required=False,
            annotation_class_id=42,
            property_values=[PropertyValue(value="Open")],
            granularity=PropertyGranularity.annotation,
        )
        assert property_key(prop) == ("Status", 42)

    def test_item_level_uses_none_for_class_id(self) -> None:
        prop = FullProperty(
            name="Status",
            type="text",
            required=False,
            annotation_class_id=None,
            granularity=PropertyGranularity.item,
        )
        assert property_key(prop) == ("Status", None)

    def test_class_level_and_item_level_with_same_name_differ(self) -> None:
        class_level = FullProperty(
            name="Status",
            type="single_select",
            required=False,
            annotation_class_id=42,
            property_values=[PropertyValue(value="Open")],
            granularity=PropertyGranularity.annotation,
        )
        item_level = FullProperty(
            name="Status",
            type="text",
            required=False,
            annotation_class_id=None,
            granularity=PropertyGranularity.item,
        )
        assert property_key(class_level) != property_key(item_level)

    def test_matches_team_property_lookups_key_order(self) -> None:
        # The contract: ``property_key(prop)`` is drop-in usable against
        # ``TeamPropertyLookups.annotation_properties`` which keys on
        # ``(name, annotation_class_id)``. Any reorder here is a breaking
        # change for every consumer that relies on that interchangeability.
        prop = FullProperty(
            name="Status",
            type="single_select",
            required=False,
            annotation_class_id=42,
            property_values=[PropertyValue(value="Open")],
            granularity=PropertyGranularity.annotation,
        )
        lookups_key = (prop.name, prop.annotation_class_id)
        assert property_key(prop) == lookups_key


class TestPropertyValueFromMetadata:
    """Direct coverage for the helper that replaced 5 copies of the
    ``PropertyValue(value=..., color=... or "auto")`` idiom."""

    def test_passes_through_value_and_color(self) -> None:
        pv = _property_value_from_metadata(
            {"value": "Red", "color": "rgba(255,0,0,1.0)"}
        )
        assert pv.value == "Red"
        assert pv.color == "rgba(255,0,0,1.0)"

    def test_defaults_missing_color_to_auto(self) -> None:
        pv = _property_value_from_metadata({"value": "Red"})
        assert pv.color == "auto"

    def test_treats_empty_color_as_missing(self) -> None:
        # ``color=""`` in metadata is treated the same as a missing key —
        # the Pydantic validator would otherwise reject it.
        pv = _property_value_from_metadata({"value": "Red", "color": ""})
        assert pv.color == "auto"


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
    """Class-level (annotation + section) coverage. Item-level lands in
    PR 2 alongside the in-batch parent-creation support."""

    def test_returns_as_is_for_top_level(self) -> None:
        prop = _make_property(name="top")
        resolved = _resolve_parent_property_for_create(
            prop, _fake_team_property_lookups()
        )
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
        resolved = _resolve_parent_property_for_create(child, lookups)
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
        resolved = _resolve_parent_property_for_create(child, lookups)
        assert resolved.parent_property_id == "notes-id"
        assert resolved.trigger_condition is not None
        assert resolved.trigger_condition.type == "any_value"
        assert resolved.trigger_condition.property_value_ids is None

    def test_missing_parent_raises(self) -> None:
        child = _make_property(
            name="child",
            parent_name="Nonexistent",
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(ValueError, match="Cannot resolve parent"):
            _resolve_parent_property_for_create(child, _fake_team_property_lookups())

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
            _resolve_parent_property_for_create(child, lookups)

    def test_value_match_with_duplicate_values_raises(self) -> None:
        # Duplicates in ``trigger.values`` are a data error: each parent
        # value should appear at most once. Surface it instead of silently
        # deduplicating.
        parent_on_server = FullProperty(
            id="p-id",
            name="Parent",
            type="multi_select",
            required=False,
            annotation_class_id=1,
            property_values=[
                PropertyValue(id="v-a", value="A"),
                PropertyValue(id="v-b", value="B"),
            ],
            granularity=PropertyGranularity.annotation,
        )
        lookups = _fake_team_property_lookups(
            annotation_properties={("Parent", 1): parent_on_server}
        )
        child = _make_property(
            name="child",
            parent_name="Parent",
            trigger_condition=TriggerCondition(
                type="value_match", values=["A", "B", "A"]
            ),
        )
        with pytest.raises(ValueError, match=r"duplicate values: \['A'\]"):
            _resolve_parent_property_for_create(child, lookups)

    def test_value_match_without_values_raises_clear_error(self) -> None:
        # Contract: darwin-py identifies parent values by name, so
        # ``value_match`` triggers must be set up with ``values``
        # (names), not ``property_value_ids`` (UUIDs). Passing UUIDs
        # alone used to silently drop them and trip an opaque validator
        # downstream; the importer now surfaces a clear error instead.
        parent_on_server = FullProperty(
            id="p-id",
            name="Parent",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="v-uuid", value="A")],
            granularity=PropertyGranularity.annotation,
        )
        lookups = _fake_team_property_lookups(
            annotation_properties={("Parent", 1): parent_on_server}
        )
        child = _make_property(
            name="child",
            parent_name="Parent",
            trigger_condition=TriggerCondition(
                type="value_match", property_value_ids=["v-uuid"]
            ),
        )
        with pytest.raises(
            ValueError, match="must set 'values' \\(parent value names\\)"
        ):
            _resolve_parent_property_for_create(child, lookups)

    def test_rejects_cross_granularity_parent(self) -> None:
        # The BE rejects cross-granularity nesting at create time. Catching
        # it client-side gives a precise error pointing at both
        # granularities, instead of the BE's generic 422.
        annotation_parent = FullProperty(
            id="p-id",
            name="Parent",
            type="single_select",
            required=False,
            annotation_class_id=1,
            property_values=[PropertyValue(id="v-uuid", value="A")],
            granularity=PropertyGranularity.annotation,
        )
        lookups = _fake_team_property_lookups(
            annotation_properties={("Parent", 1): annotation_parent}
        )
        section_child = _make_property(
            name="child",
            parent_name="Parent",
            granularity=PropertyGranularity.section,
            trigger_condition=TriggerCondition(type="any_value"),
        )
        with pytest.raises(
            ValueError,
            match=r"granularity 'annotation' but child is 'section'",
        ):
            _resolve_parent_property_for_create(section_child, lookups)


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

    def test_parse_property_classes_rejects_inconsistent_nesting_fields(self) -> None:
        # ``parent_name`` and ``trigger_condition`` are the SDK-local pair
        # that represents nesting. A metadata file with one but not the
        # other is malformed and would silently produce a degraded
        # property at create time. Fail fast at parse.
        for orphan in [
            {  # parent_name without trigger_condition
                "name": "Bad",
                "type": "text",
                "required": False,
                "granularity": "annotation",
                "property_values": [],
                "parent_name": "Parent",
            },
            {  # trigger_condition without parent_name
                "name": "Bad",
                "type": "text",
                "required": False,
                "granularity": "annotation",
                "property_values": [],
                "trigger_condition": {"type": "any_value"},
            },
        ]:
            with pytest.raises(ValueError, match="inconsistent nesting metadata"):
                parse_property_classes(
                    {
                        "classes": [
                            {
                                "name": "c",
                                "type": "polygon",
                                "description": None,
                                "properties": [orphan],
                            }
                        ]
                    }
                )


class TestImportPropertiesNestedAgainstExistingParent:
    """``_import_properties`` end-to-end with a class-level nested child
    whose parent already exists on the team. The importer must resolve
    ``parent_name`` against ``team_property_lookups`` and emit the
    resolved ``parent_property_id`` plus UUID-form trigger to the API.
    """

    @pytest.fixture
    def mock_dataset(self) -> Mock:
        dataset = Mock()
        dataset.team = "test_team"
        dataset.name = "test_dataset"
        dataset.dataset_id = 1
        return dataset

    def _metadata_with_only_child(self) -> dict:
        return {
            "classes": [
                {
                    "name": "test_class",
                    "type": "polygon",
                    "description": None,
                    "properties": [
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
                    ],
                }
            ]
        }

    def test_creates_nested_child_when_parent_already_exists_on_team(
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
                    dt.SelectedProperty(
                        frame_index=None,
                        name="Contamination Source",
                        type="single_select",
                        value="Chemical",
                    ),
                ],
            )
        ]

        # Pre-seed lookups with the parent property as if it had been
        # previously created on the team.
        existing_parent = FullProperty(
            id="existing-parent-id",
            name="Defect Type",
            type="multi_select",
            required=False,
            annotation_class_id=123,
            slug="test_team",
            property_values=[
                PropertyValue(id="existing-cont-id", value="Contamination"),
            ],
            granularity=PropertyGranularity.annotation,
        )
        mock_lookups = Mock()
        mock_lookups.annotation_properties = {
            ("Defect Type", 123): existing_parent,
        }
        mock_lookups.item_properties = {}
        mock_lookups.refresh = Mock()

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
            return server_prop

        client.create_property.side_effect = fake_create_property
        client.update_property = Mock()
        client.get_team_properties = Mock(return_value=[])

        with tempfile.TemporaryDirectory() as tmp:
            metadata_path = Path(tmp) / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(self._metadata_with_only_child(), f)

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

        assert len(created_payloads) == 1
        payload = created_payloads[0]
        assert payload.name == "Contamination Source"
        assert payload.parent_property_id == "existing-parent-id"
        assert payload.trigger_condition is not None
        assert payload.trigger_condition.type == "value_match"
        assert payload.trigger_condition.property_value_ids == ["existing-cont-id"]
