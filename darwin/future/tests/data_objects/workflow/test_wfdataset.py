from pathlib import Path

import pytest
from pydantic import ValidationError

from darwin.future.data_objects.workflow import WFDatasetCore
from darwin.future.tests.data_objects.workflow.invalidvaluefortest import (
    InvalidValueForTest,
)

test_data_path: Path = Path(__file__).parent / "data"
validate_dataset_json = test_data_path / "dataset.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_dataset_json.exists()


def test_WFDataset_validates_from_valid_json() -> None:
    WFDatasetCore.parse_file(validate_dataset_json)
    assert True


def test_cast_to_int_returns_dataset_id() -> None:
    dataset = WFDatasetCore.parse_file(validate_dataset_json)
    assert dataset.id == 101


def test_cast_to_str_returns_dataset_name() -> None:
    dataset = WFDatasetCore.parse_file(validate_dataset_json)
    assert dataset.name == "Test Dataset"


def test_sad_paths() -> None:
    dataset = WFDatasetCore.parse_file(validate_dataset_json)
    fields = ["id", "name", "instructions"]

    # Test missing fields
    for key in fields:
        with pytest.raises(ValidationError) as excinfo:
            working_dataset = dataset.model_copy().model_dump()
            del working_dataset[key]
            WFDatasetCore.model_validate(working_dataset)

        assert str(excinfo.value).startswith(
            f"1 validation error for WFDatasetCore\n{key}"
        )

    # Test invalid types
    for key in fields:
        with pytest.raises(ValidationError) as excinfo:
            working_dataset = dataset.model_copy().model_dump()
            working_dataset[key] = InvalidValueForTest()
            WFDatasetCore.model_validate(working_dataset)

        assert str(excinfo.value).startswith(
            f"1 validation error for WFDatasetCore\n{key}"
        )
