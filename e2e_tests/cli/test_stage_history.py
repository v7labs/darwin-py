import copy
import json
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List

import pytest
import requests

from darwin.dataset.stage_history import read_stage_history
from e2e_tests.helpers import (
    api_headers,
    assert_cli,
    create_workflow,
    export_release,
    run_cli_command,
    run_item_commands,
    wait_for_item_stage,
)
from e2e_tests.objects import (
    ConfigValues,
    E2EDataset,
    get_read_only_registration_payload,
)
from e2e_tests.setup_tests import create_annotation_class

# Actor rows are not snapshotted, so authorship is the only allowed difference
AUTHORSHIP_FIELDS = ("annotators", "reviewers", "updated_at")


def skip_unless_stage_history_supported(
    config_values: ConfigValues, dataset: E2EDataset
) -> None:
    # Backends with the option reject it for non-Darwin formats; older ones ignore it
    response = requests.post(
        f"{config_values.server}/api/v2/teams/{config_values.team_slug}/datasets/{dataset.slug}/exports",
        json={
            "name": "stage-history-probe",
            "format": "coco",
            "include_stage_history": True,
            "include_authorship": False,
            "include_export_token": False,
        },
        headers=api_headers(config_values),
    )
    if not (
        response.status_code == 422
        and "STAGE_HISTORY_REQUIRES_DARWIN_JSON" in response.text
    ):
        pytest.skip(
            "The E2E backend doesn't support include_stage_history yet "
            "(darwin-backend #6307 not deployed)"
        )


def create_property(config_values: ConfigValues, payload: dict) -> dict:
    response = requests.post(
        f"{config_values.server}/api/v2/teams/{config_values.team_slug}/properties",
        json=payload,
        headers=api_headers(config_values),
    )
    assert response.ok, response.text
    return response.json()


def value_ids(prop: dict) -> Dict[str, str]:
    return {value["value"]: value["id"] for value in prop["property_values"]}


def register_one_image(config_values: ConfigValues, dataset: E2EDataset) -> dict:
    payload = get_read_only_registration_payload("single_slotted", dataset.slug)
    payload["items"] = payload["items"][:1]
    response = requests.post(
        f"{config_values.server}/api/v2/teams/{config_values.team_slug}/items/register_existing_readonly",
        json=payload,
        headers=api_headers(config_values),
    )
    assert response.ok, response.text
    return response.json()["items"][0]


def export_item_file(
    config_values: ConfigValues, dataset: E2EDataset, item_id: str, name: str
) -> dict:
    """Runs a normal Darwin JSON export and returns the item's file."""
    release = export_release("darwin", dataset, config_values, release_name=name)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = release.download_zip(Path(tmp) / "export.zip")
        with zipfile.ZipFile(zip_path) as z:
            names = z.namelist()
            assert not any(n.startswith("stage_history/") for n in names)
            files = [json.loads(z.read(n)) for n in names if "/" not in n]
    return next(f for f in files if f["item"]["source_info"]["item_id"] == item_id)


def without_authorship(darwin_json: dict) -> dict:
    data = copy.deepcopy(darwin_json)
    for annotation in data["annotations"]:
        for field in AUTHORSHIP_FIELDS:
            annotation.pop(field, None)
    return data


def polygon(x: int, y: int) -> dict:
    return {
        "polygon": {
            "path": [
                {"x": x, "y": y},
                {"x": x + 10, "y": y},
                {"x": x, "y": y + 10},
            ]
        }
    }


def test_full_cycle_stage_history(
    local_dataset: E2EDataset, config_values: ConfigValues
):
    """
    Moves an item Dataset -> Annotate -> Review -(reject)-> Annotate -(set_stage)-> Review
    -(approve)-> Complete, changing annotations, annotation properties and item properties in
    every visit and taking a normal export before each visit ends. The full-history export
    must hold, per visit, a snapshot equal to that export (authorship aside).
    """
    skip_unless_stage_history_supported(config_values, local_dataset)
    suffix = uuid.uuid4().hex[:6]

    shape_class = create_annotation_class(
        f"test_stage_history_polygon_{suffix}",
        "polygon",
        config_values,
        fixed_name=True,
    )
    tag_class = create_annotation_class(
        f"test_stage_history_tag_{suffix}", "tag", config_values, fixed_name=True
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
    verdict = create_property(
        config_values,
        {
            "name": f"test_stage_history_verdict_{suffix}",
            "type": "single_select",
            "granularity": "item",
            "required": True,
            "dataset_ids": [local_dataset.id],
            "property_values": [
                {"value": "pass", "color": "rgba(255,92,0,1.0)"},
                {"value": "fail", "color": "rgba(255,92,0,1.0)"},
            ],
        },
    )
    comment = create_property(
        config_values,
        {
            "name": f"test_stage_history_comment_{suffix}",
            "type": "text",
            "granularity": "item",
            "required": False,
            "dataset_ids": [local_dataset.id],
        },
    )
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
        f"test_stage_history_{suffix}",
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
    item = register_one_image(config_values, local_dataset)
    item_id = item["id"]
    slot_name = item["slots"][0]["slot_name"]
    wait_for_item_stage(config_values, local_dataset.id, item_id, stage_ids["dataset"])

    def at(stage: str, command_type: str, **data) -> dict:
        return {"type": command_type, "data": {"stage_id": stage_ids[stage], **data}}

    def create(stage: str, annotation_id: str, class_id: int, data: dict, props: dict):
        return at(
            stage,
            "create_annotation",
            annotation_id=annotation_id,
            annotation_class_id=class_id,
            data=data,
            metadata={},
            context_keys={"slot_names": [slot_name]},
            properties={"global": props},
        )

    def update(stage: str, annotation_id: str, data=None, props=None):
        return at(
            stage,
            "update_annotation",
            annotation_id=annotation_id,
            data=data,
            metadata={},
            properties=None if props is None else {"global": props},
        )

    def delete(stage: str, annotation_id: str) -> dict:
        return at(stage, "delete_annotation", annotation_id=annotation_id)

    def item_properties(stage: str, props: dict) -> dict:
        return at(stage, "set_item_properties", properties=props)

    def transition(stage: str, edge_name: str = "default") -> dict:
        return at(stage, "transition_via_edge", edge=edge_name)

    def move_to(stage: str) -> dict:
        return {"type": "set_stage", "data": {"to_stage_id": stage_ids[stage]}}

    def end_visit(name: str, commands: List[dict], move: dict, next_stage: str):
        run_item_commands(config_values, item_id, commands)
        exports.append(export_item_file(config_values, local_dataset, item_id, name))
        run_item_commands(config_values, item_id, [move])
        wait_for_item_stage(
            config_values, local_dataset.id, item_id, stage_ids[next_stage]
        )

    shape, label, extra, label_2 = (str(uuid.uuid4()) for _ in range(4))
    exports: List[dict] = []

    end_visit(
        "visit-1-dataset",
        [
            create(
                "dataset",
                shape,
                shape_class.id,
                polygon(10, 10),
                {quality["id"]: [good]},
            ),
            create("dataset", label, tag_class.id, {"tag": {}}, {}),
            item_properties("dataset", {verdict["id"]: [passed]}),
        ],
        transition("dataset"),
        "annotate",
    )
    end_visit(
        "visit-2-annotate",
        [
            update("annotate", shape, polygon(20, 20), {quality["id"]: [bad]}),
            delete("annotate", label),
            create(
                "annotate",
                extra,
                shape_class.id,
                polygon(50, 50),
                {note["id"]: [{"text": "second"}]},
            ),
            item_properties("annotate", {comment["id"]: [{"text": "first pass"}]}),
        ],
        transition("annotate"),
        "review",
    )
    end_visit(
        "visit-3-review",
        [
            update("review", shape, polygon(30, 30)),
            update("review", extra, props={note["id"]: [{"text": "check this"}]}),
            item_properties("review", {comment["id"]: [{"text": "redo"}]}),
        ],
        transition("review", "reject"),
        "annotate",
    )
    end_visit(
        "visit-4-annotate",
        [
            delete("annotate", extra),
            update("annotate", shape, props={quality["id"]: []}),
            item_properties("annotate", {verdict["id"]: [failed]}),
        ],
        move_to("review"),
        "review",
    )
    end_visit(
        "visit-5-review",
        [
            create("review", label_2, tag_class.id, {"tag": {}}, {}),
            update("review", shape, props={note["id"]: [{"text": "looks fine"}]}),
            item_properties("review", {verdict["id"]: [passed]}),
        ],
        transition("review", "approve"),
        "complete",
    )

    release_name = "full-stage-history"
    result = run_cli_command(
        f"darwin dataset export {local_dataset.name} {release_name} --version 2.0 --include-stage-history"
    )
    assert_cli(result, 0)
    result = run_cli_command(
        f"darwin dataset pull {local_dataset.name}:{release_name} --only-annotations --retry"
    )
    assert_cli(result, 0)

    release_dir = (
        Path.home()
        / ".darwin"
        / "datasets"
        / config_values.team_slug
        / local_dataset.slug
        / "releases"
        / release_name
    )
    visits = read_stage_history(release_dir / "stage_history" / item_id)
    user_id = requests.get(
        f"{config_values.server}/api/users/token_info",
        headers=api_headers(config_values),
    ).json()["id"]

    assert [(v.stage["name"], v.status) for v in visits] == [
        ("Dataset", "completed"),
        ("Annotate", "completed"),
        ("Review", "completed"),
        ("Annotate", "overriden"),
        ("Review", "completed"),
        ("Complete", "current"),
    ]
    assert [v.stage["id"] for v in visits] == [
        stage_ids[s]
        for s in ("dataset", "annotate", "review", "annotate", "review", "complete")
    ]
    assert all(v.exited_by == {"type": "user", "id": user_id} for v in visits[:-1])
    assert visits[-1].exited_by is None and visits[-1].exited_at is None
    assert visits[-1].exit_snapshot["status"] == "none"
    assert visits[-1].snapshot_path is None

    assert len({json.dumps(e, sort_keys=True) for e in exports}) == len(exports)
    for visit, expected in zip(visits, exports):
        assert visit.exit_snapshot == {
            "status": "exported",
            "file": f"{visit.stage_instance_id}.json",
        }
        snapshot = json.loads(visit.snapshot_path.read_text())
        assert not any(
            field in annotation
            for annotation in snapshot["annotations"]
            for field in ("annotators", "reviewers")
        )
        assert without_authorship(snapshot) == without_authorship(expected), visit.stage
        parsed = visit.snapshot()
        assert parsed is not None
        assert sorted(a.id for a in parsed.annotations) == sorted(
            a["id"] for a in expected["annotations"]
        )

    # The live file is unchanged by the option
    (live_path,) = (release_dir / "annotations").glob("*.json")
    live = json.loads(live_path.read_text())
    assert without_authorship(live) == without_authorship(exports[-1])
