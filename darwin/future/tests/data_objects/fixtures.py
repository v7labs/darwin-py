from pathlib import Path

import pytest

test_data_path: Path = Path(__file__).parent / "workflow" / "data"
valid_stage_json = test_data_path / "stage.json"
valid_workflow_json = test_data_path / "workflow.json"


@pytest.fixture
def basic_team() -> dict:
    return {"slug": "test-team", "id": 0, "name": "test-team"}


@pytest.fixture
def basic_dataset() -> dict:
    return {"name": "test-dataset", "slug": "test-dataset"}


@pytest.fixture
def basic_release() -> dict:
    return {"name": "test-release"}


@pytest.fixture
def basic_combined(basic_team: dict, basic_dataset: dict, basic_release: dict) -> dict:
    combined = basic_team
    combined["datasets"] = [basic_dataset]
    combined["datasets"][0]["releases"] = [basic_release]
    return combined


@pytest.fixture
def broken_combined(basic_combined: dict) -> dict:
    del basic_combined["datasets"][0]["name"]
    return basic_combined
