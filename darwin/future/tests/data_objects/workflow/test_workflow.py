from datetime import datetime
from pathlib import Path
from uuid import UUID

from darwin.future.data_objects.workflow import WFDatasetCore, WFStageCore, WorkflowCore

test_data_path: Path = Path(__file__).parent / "data"
validate_json = test_data_path / "workflow.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_json.exists()


def test_Workflow_validates_from_valid_json() -> None:
    parsed_set = WorkflowCore.parse_file(validate_json)

    assert isinstance(parsed_set, WorkflowCore)
    assert isinstance(parsed_set.id, UUID)
    assert isinstance(parsed_set.name, str)
    assert isinstance(parsed_set.team_id, int)

    assert isinstance(parsed_set.stages, list)
    assert all(isinstance(i, WFStageCore) for i in parsed_set.stages)
    assert isinstance(parsed_set.dataset, WFDatasetCore)

    assert isinstance(parsed_set.inserted_at, datetime)
    assert isinstance(parsed_set.updated_at, datetime)

    assert isinstance(parsed_set.thumbnails, list)
    assert all(isinstance(i, str) for i in parsed_set.thumbnails)
