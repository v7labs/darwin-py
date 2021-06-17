import json
import shutil
from pathlib import Path

import pytest

DARWIN_DATASET_NAME = "test_dataset"
DARWIN_TEAM_NAME = "v7"
DARWIN_TEST_PATH = Path("/tmp/darwin-test")


def create_annotation_file(
    *, name: str, content: dict, team_name: str, dataset_name: str, release_name: str = "latest"
):
    annotations_path = DARWIN_TEST_PATH / team_name / dataset_name / "releases" / release_name / "annotations"
    annotations_path.mkdir(exist_ok=True, parents=True)

    with (annotations_path / name).open("w") as f:
        json.dump(content, f)


@pytest.fixture
def team_name():
    return DARWIN_TEAM_NAME


@pytest.fixture
def dataset_name(team_name):
    return DARWIN_DATASET_NAME


@pytest.fixture
def file_read_write_test(team_name, dataset_name):
    # Executed before the test
    _setup_darwin_test_path(team_name=team_name, dataset_name=dataset_name)

    # Useful if the test needs to reuse attrs
    yield

    # Executed after the test
    shutil.rmtree(DARWIN_TEST_PATH)


# Private


def _setup_darwin_test_path(*, team_name: str, dataset_name: str):
    dataset_path = DARWIN_TEST_PATH / team_name / dataset_name
    dataset_path.mkdir(exist_ok=True, parents=True)
