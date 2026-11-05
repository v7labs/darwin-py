import json
import tempfile
import uuid
from pathlib import Path
from typing import List

from darwin.dataset.stage_history import StageVisit, read_stage_history
from e2e_tests.cli.test_stage_history import (
    create_property,
    export_item_file,
    polygon,
    skip_unless_stage_history_supported,
    value_ids,
)
from e2e_tests.helpers import (
    assert_cli,
    create_workflow,
    run_cli_command,
    run_item_commands,
    wait_for_item_stage,
    wait_until_items_processed,
)
from e2e_tests.objects import ConfigValues, E2EDataset
from e2e_tests.setup_tests import (
    create_annotation_class,
    create_item,
    create_random_image,
)

# The import recreates annotations, so these are the fields a restore can't keep
REGENERATED_FIELDS = ("id", "annotators", "reviewers", "updated_at")


def restorable_state(darwin_json: dict) -> dict:
    """Annotations (order-free, IDs and authorship aside) and item properties of a file."""
    annotations = [
        {k: v for k, v in annotation.items() if k not in REGENERATED_FIELDS}
        for annotation in darwin_json["annotations"]
    ]
    return {
        "annotations": sorted(annotations, key=lambda a: json.dumps(a, sort_keys=True)),
        "properties": sorted(
            darwin_json.get("properties", []),
            key=lambda p: json.dumps(p, sort_keys=True),
        ),
    }


def annotation_property_values(darwin_json: dict) -> List[list]:
    return sorted(
        sorted((p["name"], p["value"]) for p in annotation.get("properties", []))
        for annotation in darwin_json["annotations"]
    )


def item_property_values(darwin_json: dict) -> dict:
    return {p["name"]: p["value"] for p in darwin_json.get("properties", [])}


def export_and_pull_history(
    dataset: E2EDataset, config_values: ConfigValues, item_id: str, release_name: str
) -> List[StageVisit]:
    result = run_cli_command(
        f"darwin dataset export {dataset.name} {release_name} --version 2.0 --include-stage-history"
    )
    assert_cli(result, 0)
    result = run_cli_command(
        f"darwin dataset pull {dataset.name}:{release_name} --only-annotations --retry"
    )
    assert_cli(result, 0)
    release_dir = (
        Path.home()
        / ".darwin"
        / "datasets"
        / config_values.team_slug
        / dataset.slug
        / "releases"
        / release_name
    )
    return read_stage_history(release_dir / "stage_history" / item_id)


def test_restore_item_from_stage_history(
    local_dataset: E2EDataset, config_values: ConfigValues
):
    """
    Annotates an item, rejects it in Review and reworks it in a second Annotate visit, then
    imports the first Annotate visit's exit snapshot with `--overwrite`. The item's
    annotations, annotation properties and item properties must equal that snapshot, and
    the restored state must itself be recorded as the next visit's snapshot.
    """
    skip_unless_stage_history_supported(config_values, local_dataset)
    suffix = uuid.uuid4().hex[:6]

    shape_class = create_annotation_class(
        f"test_stage_history_restore_{suffix}",
        "polygon",
        config_values,
        fixed_name=True,
    )
    quality = create_property(
        config_values,
        {
            "name": "quality",
            "type": "single_select",
            "granularity": "annotation",
            "required": False,
            "annotation_class_id": shape_class.id,
            "property_values": [
                {"type": "string", "value": "good", "color": "auto"},
                {"type": "string", "value": "bad", "color": "auto"},
            ],
        },
    )
    note = create_property(
        config_values,
        {
            "name": "note",
            "type": "text",
            "granularity": "annotation",
            "required": False,
            "annotation_class_id": shape_class.id,
            "property_values": [],
        },
    )

    def item_property(name: str, prop_type: str, values: List[str]) -> dict:
        return create_property(
            config_values,
            {
                "name": f"test_stage_history_restore_{name}_{suffix}",
                "type": prop_type,
                "granularity": "item",
                "required": False,
                "dataset_ids": [local_dataset.id],
                "property_values": [
                    {"value": value, "color": "rgba(255,92,0,1.0)"} for value in values
                ],
            },
        )

    verdict = item_property("verdict", "single_select", ["pass", "fail"])
    comment = item_property("comment", "text", [])
    # Only set after the restored visit, so the restore must clear it
    extra = item_property("extra", "text", [])
    good, bad = value_ids(quality)["good"], value_ids(quality)["bad"]
    passed, failed = value_ids(verdict)["pass"], value_ids(verdict)["fail"]

    stage_ids = {
        name: str(uuid.uuid4())
        for name in ("dataset", "annotate", "review", "complete")
    }

    def edge(name: str, source: str, target: str) -> dict:
        return {
            "name": name,
            "source_stage_id": stage_ids[source],
            "target_stage_id": stage_ids[target],
        }

    create_workflow(
        config_values,
        f"test_stage_history_restore_{suffix}",
        [
            {
                "id": stage_ids["dataset"],
                "name": "Dataset",
                "type": "dataset",
                "config": {
                    "initial": True,
                    "dataset_id": local_dataset.id,
                    "x": 0,
                    "y": 0,
                },
                "edges": [edge("default", "dataset", "annotate")],
            },
            {
                "id": stage_ids["annotate"],
                "name": "Annotate",
                "type": "annotate",
                "config": {"assignable_to": "anyone", "x": 100, "y": 0},
                "edges": [edge("default", "annotate", "review")],
            },
            {
                "id": stage_ids["review"],
                "name": "Review",
                "type": "review",
                "config": {"assignable_to": "anyone", "x": 200, "y": 0},
                "edges": [
                    edge("approve", "review", "complete"),
                    edge("reject", "review", "annotate"),
                ],
            },
            {
                "id": stage_ids["complete"],
                "name": "Complete",
                "type": "complete",
                "config": {"x": 300, "y": 0},
                "edges": [],
            },
        ],
    )
    # Uploaded rather than registered, so the team needs no external storage
    with tempfile.TemporaryDirectory() as tmp:
        item = create_item(
            local_dataset.slug,
            suffix,
            create_random_image(suffix, Path(tmp)),
            config_values,
        )
    item_id, slot_name = item.id, item.slot_name
    wait_until_items_processed(config_values, local_dataset.id)
    wait_for_item_stage(config_values, local_dataset.id, item_id, stage_ids["dataset"])

    def at(stage: str, command_type: str, **data) -> dict:
        return {"type": command_type, "data": {"stage_id": stage_ids[stage], **data}}

    def create(annotation_id: str, data: dict, props: dict) -> dict:
        return at(
            "annotate",
            "create_annotation",
            annotation_id=annotation_id,
            annotation_class_id=shape_class.id,
            data=data,
            metadata={},
            context_keys={"slot_names": [slot_name]},
            properties={"global": props},
        )

    def finish_visit(stage: str, commands: List[dict], edge_name: str, next_stage: str):
        run_item_commands(
            config_values,
            item_id,
            [*commands, at(stage, "transition_via_edge", edge=edge_name)],
        )
        wait_for_item_stage(
            config_values, local_dataset.id, item_id, stage_ids[next_stage]
        )

    kept, dropped, added = (str(uuid.uuid4()) for _ in range(3))
    finish_visit("dataset", [], "default", "annotate")
    finish_visit(
        "annotate",
        [
            create(
                kept,
                polygon(10, 10),
                {quality["id"]: [good], note["id"]: [{"text": "first"}]},
            ),
            create(dropped, polygon(50, 50), {quality["id"]: [bad]}),
            at(
                "annotate",
                "set_item_properties",
                properties={
                    verdict["id"]: [passed],
                    comment["id"]: [{"text": "first pass"}],
                },
            ),
        ],
        "default",
        "review",
    )
    finish_visit("review", [], "reject", "annotate")
    finish_visit(
        "annotate",
        [
            at("annotate", "delete_annotation", annotation_id=dropped),
            at(
                "annotate",
                "update_annotation",
                annotation_id=kept,
                data=polygon(30, 30),
                metadata={},
                properties={
                    "global": {quality["id"]: [bad], note["id"]: [{"text": "moved"}]}
                },
            ),
            create(added, polygon(70, 70), {}),
            at(
                "annotate",
                "set_item_properties",
                properties={
                    verdict["id"]: [failed],
                    comment["id"]: [{"text": "second pass"}],
                    extra["id"]: [{"text": "added later"}],
                },
            ),
        ],
        "default",
        "review",
    )
    # The CLI exports only complete items, so each export waits for Complete
    finish_visit("review", [], "approve", "complete")

    visits = export_and_pull_history(
        local_dataset, config_values, item_id, "history-before-restore"
    )
    assert [(v.stage["name"], v.status) for v in visits] == [
        ("Dataset", "completed"),
        ("Annotate", "completed"),
        ("Review", "completed"),
        ("Annotate", "completed"),
        ("Review", "completed"),
        ("Complete", "current"),
    ]
    chosen = visits[1]
    snapshot = json.loads(chosen.snapshot_path.read_text())
    reworked = json.loads(visits[3].snapshot_path.read_text())
    assert annotation_property_values(snapshot) == [
        [("note", "first"), ("quality", "good")],
        [("quality", "bad")],
    ]
    assert annotation_property_values(reworked) == [
        [],
        [("note", "moved"), ("quality", "bad")],
    ]
    assert item_property_values(snapshot) == {
        verdict["name"]: "pass",
        comment["name"]: "first pass",
    }
    assert item_property_values(reworked) == {
        verdict["name"]: "fail",
        comment["name"]: "second pass",
        extra["name"]: "added later",
    }

    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {chosen.snapshot_path} --overwrite --yes"
    )
    assert_cli(result, 0)

    restored = export_item_file(config_values, local_dataset, item_id, "restored")
    assert restorable_state(restored) == restorable_state(snapshot)
    # Known limitation: the restore recreates annotations instead of reviving them
    assert not {a["id"] for a in restored["annotations"]} & {
        a["id"] for a in snapshot["annotations"]
    }

    # Send the item back through Review: the visit that held the restore records it
    run_item_commands(
        config_values,
        item_id,
        [{"type": "set_stage", "data": {"to_stage_id": stage_ids["review"]}}],
    )
    wait_for_item_stage(config_values, local_dataset.id, item_id, stage_ids["review"])
    finish_visit("review", [], "approve", "complete")
    visits = export_and_pull_history(
        local_dataset, config_values, item_id, "history-after-restore"
    )
    assert [v.stage["name"] for v in visits][5:] == ["Complete", "Review", "Complete"]
    for visit in visits[5:7]:
        recorded = json.loads(visit.snapshot_path.read_text())
        assert restorable_state(recorded) == restorable_state(snapshot), visit.stage
        assert sorted(a["id"] for a in recorded["annotations"]) == sorted(
            a["id"] for a in restored["annotations"]
        )
