import json
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from darwin.client import Client
from darwin.config import Config
from darwin.dataset.release import Release, ReleaseStatus
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.dataset.stage_history import read_stage_history
from tests.fixtures import *  # noqa: F401, F403

ITEM_ID = "0190f3c1-7a3c-7d5a-9d8e-3b5f0e8c1a11"
ANNOTATE_VISIT = "0190f3c1-7a3c-7d5a-9d8e-3b5f0e8c1a22"
COMPLETE_VISIT = "0190f3c1-7a3c-7d5a-9d8e-3b5f0e8c1a33"


@pytest.fixture
def darwin_client(
    darwin_config_path: Path, darwin_datasets_path: Path, team_slug_darwin_json_v2: str
) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug_darwin_json_v2, "api_key"], "mock_api_key")
    config.put(
        ["teams", team_slug_darwin_json_v2, "datasets_dir"], str(darwin_datasets_path)
    )
    return Client(config=config)


def visits_json() -> dict:
    return {
        "version": "1.0",
        "item_id": ITEM_ID,
        "visits": [
            {
                "stage_instance_id": ANNOTATE_VISIT,
                "parent_stage_id": None,
                "stage": {"id": "s1", "name": "Annotate", "type": "annotate"},
                "status": "completed",
                "entered_at": "2026-10-01T10:00:00Z",
                "exited_at": "2026-10-01T11:00:00.000000Z",
                "exited_by": {"type": "user", "id": 123},
                "exit_snapshot": {
                    "status": "exported",
                    "file": f"{ANNOTATE_VISIT}.json",
                },
            },
            {
                "stage_instance_id": COMPLETE_VISIT,
                "parent_stage_id": None,
                "stage": {"id": "s2", "name": "Complete", "type": "complete"},
                "status": "current",
                "entered_at": "2026-10-01T11:00:00Z",
                "exited_at": None,
                "exited_by": None,
                "exit_snapshot": {"status": "none", "file": None},
            },
        ],
    }


def snapshot_json() -> dict:
    return {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "image.jpg",
            "path": "/",
            "source_info": {
                "item_id": ITEM_ID,
                "dataset": {"name": "ds", "slug": "ds", "dataset_management_url": ""},
                "team": {"name": "team", "slug": "team"},
                "workview_url": "",
            },
            "slots": [
                {
                    "type": "image",
                    "slot_name": "0",
                    "width": 100,
                    "height": 50,
                    "source_files": [{"file_name": "image.jpg", "url": ""}],
                }
            ],
        },
        "annotations": [
            {
                "id": "a1",
                "name": "box",
                "bounding_box": {"x": 1, "y": 2, "w": 3, "h": 4},
                "slot_names": ["0"],
            }
        ],
        "properties": [{"name": "verdict", "value": "pass"}],
    }


def write_history(directory: Path) -> Path:
    item_dir = directory / ITEM_ID
    item_dir.mkdir(parents=True)
    (item_dir / "visits.json").write_text(json.dumps(visits_json()))
    (item_dir / f"{ANNOTATE_VISIT}.json").write_text(json.dumps(snapshot_json()))
    return item_dir


class TestReadStageHistory:
    def test_reads_visits_in_order_with_their_snapshots(self, tmp_path: Path):
        item_dir = write_history(tmp_path)

        annotate, complete = read_stage_history(item_dir)

        assert annotate.stage_instance_id == ANNOTATE_VISIT
        assert annotate.stage == {"id": "s1", "name": "Annotate", "type": "annotate"}
        assert annotate.status == "completed"
        assert annotate.exited_by == {"type": "user", "id": 123}
        assert annotate.snapshot_path == item_dir / f"{ANNOTATE_VISIT}.json"
        snapshot = annotate.snapshot()
        assert snapshot is not None
        assert snapshot.item_id == ITEM_ID
        assert [a.id for a in snapshot.annotations] == ["a1"]
        assert snapshot.annotations[0].data == {"x": 1, "y": 2, "w": 3, "h": 4}
        assert snapshot.item_properties == [{"name": "verdict", "value": "pass"}]

        assert complete.status == "current"
        assert complete.exited_at is None
        assert complete.exited_by is None
        assert complete.snapshot_path is None
        assert complete.snapshot() is None


@pytest.mark.usefixtures("file_read_write_test")
class TestPullKeepsStageHistory:
    @pytest.mark.parametrize("pretty_print", [False, True])
    def test_moves_stage_history_beside_annotations(
        self, remote_dataset: RemoteDatasetV2, tmp_path: Path, pretty_print: bool
    ):
        release = Release(
            remote_dataset.slug,
            remote_dataset.team,
            "0.1.0",
            "with-history",
            ReleaseStatus("complete"),
            "http://darwin-fake-url.com",
            datetime.now(),
            None,
            None,
            False,
            True,
            "darwin_json_2",
        )
        archive = tmp_path / "export.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("image.json", json.dumps(snapshot_json()))
            z.writestr(
                f"stage_history/{ITEM_ID}/visits.json", json.dumps(visits_json())
            )
            z.writestr(
                f"stage_history/{ITEM_ID}/{ANNOTATE_VISIT}.json",
                json.dumps(snapshot_json()),
            )

        def download_zip(path):
            path.write_bytes(archive.read_bytes())
            return path

        release_dir = remote_dataset.local_releases_path / release.name
        stale = release_dir / "stage_history" / "stale-item" / "visits.json"
        stale.parent.mkdir(parents=True)
        stale.write_text("{}")

        with patch.object(Release, "download_zip", side_effect=download_zip):
            remote_dataset.pull(
                release=release, only_annotations=True, pretty_print=pretty_print
            )

        assert [p.name for p in (release_dir / "annotations").glob("*.json")] == [
            "image.json"
        ]
        assert not stale.exists()
        visits = read_stage_history(release_dir / "stage_history" / ITEM_ID)
        assert [v.stage_instance_id for v in visits] == [ANNOTATE_VISIT, COMPLETE_VISIT]
        assert visits[0].snapshot() is not None
        for name, content in [
            ("visits.json", visits_json()),
            (f"{ANNOTATE_VISIT}.json", snapshot_json()),
        ]:
            raw = (release_dir / "stage_history" / ITEM_ID / name).read_text()
            assert json.loads(raw) == content
            assert ("\n  " in raw) is pretty_print


@pytest.mark.usefixtures("file_read_write_test")
class TestExportIncludeStageHistory:
    @responses.activate
    @pytest.mark.parametrize("include_stage_history", [False, True])
    def test_sends_option_only_when_set(
        self, remote_dataset: RemoteDatasetV2, include_stage_history: bool
    ):
        responses.add(
            responses.POST,
            "http://localhost/api/v2/teams/v7-darwin-json-v2/datasets/test-dataset/exports",
            json={},
            status=200,
        )

        remote_dataset.export(
            "release", version="2.0", include_stage_history=include_stage_history
        )

        payload = json.loads(responses.calls[0].request.body)
        assert payload["format"] == "darwin_json_2"
        assert payload.get("include_stage_history", False) is include_stage_history

    def test_rejects_darwin_json_1(self, remote_dataset: RemoteDatasetV2):
        with pytest.raises(ValueError, match="Darwin JSON 2.0"):
            remote_dataset.export("release", version="1.0", include_stage_history=True)
