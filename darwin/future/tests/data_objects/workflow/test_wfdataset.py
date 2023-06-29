from pathlib import Path

import pytest

from darwin.future.data_objects.workflow import (
    WFDataset,
)

test_data_path: Path = Path(__file__).parent / "data"
validate_dataset_json = test_data_path / "dataset.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_dataset_json.exists()


def test_WFDataset_validates_from_valid_json() -> None:
    WFDataset.parse_file(validate_dataset_json)
    assert True


def test_cast_to_int_returns_dataset_id() -> None:
    dataset = WFDataset.parse_file(validate_dataset_json)
    assert dataset.id == 101


def test_cast_to_str_returns_dataset_name() -> None:
    dataset = WFDataset.parse_file(validate_dataset_json)
    assert dataset.name == "test_dataset"
