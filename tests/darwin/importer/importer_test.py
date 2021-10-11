import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest
import responses
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.release import Release
from darwin.importer.formats.darwin import parse_file
from darwin.importer.importer import import_annotations
from tests.darwin.dataset.remote_dataset_test import files_content
from tests.fixtures import *


@pytest.fixture
def annotation_name() -> str:
    return "0.json"


# duplicate, copied from tests/dataset/remote_dataset_test.py
@pytest.fixture
def darwin_client(darwin_config_path: Path, darwin_datasets_path: Path, team_slug: str) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug, "api_key"], "mock_api_key")
    config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
    return Client(config)


@pytest.fixture
def annotation_content() -> Dict[str, Any]:
    return {
        "dataset": "test",
        "image": {
            "width": 256,
            "height": 256,
            "original_filename": "1.png",
            "filename": "1.png",
            "path": "/",
        },
        "annotations": [
            {
                "name": "baa",
                "bounding_box": {"h": 181, "w": 118, "x": 40, "y": 85},
                "polygon": {
                    "path": [{"x": 40, "y": 141}, {"x": 118, "y": 85}, {"x": 196, "y": 62}, {"x": 221, "y": 256}]
                },
            },
            {
                "name": "foo",
                "bounding_box": {"h": 115, "w": 60, "x": 141, "y": 196},
                "polygon": {
                    "path": [{"x": 256, "y": 85}, {"x": 196, "y": 62}, {"x": 221, "y": 256}, {"x": 256, "y": 203}]
                },
            },
            {
                "name": "foo",
                "bounding_box": {"h": 138, "w": 40, "x": 118, "y": 62},
                "polygon": {
                    "path": [{"x": 256, "y": 102}, {"x": 40, "y": 141}, {"x": 118, "y": 203}, {"x": 256, "y": 102}]
                },
            },
        ],
    }


@pytest.fixture
def create_annotation_files(
    darwin_datasets_path: Path,
    team_slug: str,
    dataset_slug: str,
    release_name: str,
    annotation_name: str,
    annotation_content: dict,
):
    annotations: Path = darwin_datasets_path / team_slug / dataset_slug / "releases" / release_name / "annotations"
    annotations.mkdir(exist_ok=True, parents=True)

    with (annotations / annotation_name).open("w") as f:
        json.dump(annotation_content, f)

    for i in range(1, 10):
        shutil.copy(annotations / annotation_name, annotations / f"{i}.json")


@pytest.mark.usefixtures("file_read_write_test", "create_annotation_files", "files_content")
def describe_import_annotations():
    @responses.activate
    def it_works(
        darwin_client: Client,
        files_content: Dict,
        release_name: str,
        darwin_datasets_path: Path,
        dataset_name: str,
        dataset_slug: str,
        team_slug: str,
    ):
        remote_dataset = RemoteDataset(
            client=darwin_client, team=team_slug, name=dataset_name, slug=dataset_slug, dataset_id=1
        )
        url = "http://localhost/api/dataset_items/0/import"
        responses.add(
            responses.GET,
            "http://localhost/api/teams/v7/annotation_classes?include_tags=true",
            json={"annotation_classes": [{"datasets": [{"id": -1}], "annotation_types": "polygon"}]},
            status=200,
        )

        responses.add(
            responses.GET,
            "http://localhost/api/datasets/1/attributes",
            json={},
            status=200,
        )

        responses.add(
            responses.POST,
            "http://localhost/api/datasets/1/items?page%5Bsize%5D=500",
            json=files_content,
            status=200,
        )

        responses.add(
            responses.POST,
            url,
            json={},
            status=200,
        )

        annotations_root: Path = (
            darwin_datasets_path / team_slug / dataset_slug / "releases" / release_name / "annotations"
        )

        annotations_paths: List[Path] = list(annotations_root.glob("*.json"))
        print(annotations_paths)
        # print(list(annotations_paths))

        import_annotations(remote_dataset, parse_file, annotations_paths, append=False, force=True)
        assert False
