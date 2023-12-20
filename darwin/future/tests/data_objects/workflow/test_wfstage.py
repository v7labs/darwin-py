from json import loads
from uuid import UUID

import pytest
from pydantic import ValidationError

from darwin.future.data_objects.workflow import WFStageCore
from darwin.future.tests.data_objects.fixtures import test_data_path

validate_json = test_data_path / "stage.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_json.exists()


def test_WFStage_validates_from_valid_json() -> None:
    WFStageCore.parse_file(validate_json)
    assert True


def test_casts_strings_to_uuids_as_needed() -> None:
    parsed_stage = WFStageCore.parse_file(validate_json)
    assert isinstance(parsed_stage.id, UUID)
    assert str(parsed_stage.id) == "e69d3ebe-6ab9-4159-b44f-2bf84d29bb20"


def test_raises_with_invalid_uuid() -> None:
    dict_from_json = loads(validate_json.read_text())
    dict_from_json["id"] = "not-a-uuid"

    with pytest.raises(ValidationError) as excinfo:
        WFStageCore.model_validate(dict_from_json)

    assert str(excinfo.value).startswith("1 validation error for WFStageCore\nid")
