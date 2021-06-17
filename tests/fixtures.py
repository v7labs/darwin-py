import shutil
from pathlib import Path

import pytest


@pytest.fixture
def darwin_path(tmp_path: Path) -> Path:
    return tmp_path / "darwin-test"


@pytest.fixture
def team_name() -> str:
    return "v7"


@pytest.fixture
def dataset_name() -> str:
    return "test_dataset"


@pytest.fixture
def release_name() -> str:
    return "latest"


@pytest.fixture
def file_read_write_test(darwin_path: Path, team_name: str, dataset_name: str):
    # Executed before the test
    dataset_path = darwin_path / "datasets" / team_name / dataset_name
    dataset_path.mkdir(parents=True)

    # Useful if the test needs to reuse attrs
    yield

    # Executed after the test
    shutil.rmtree(darwin_path)

