from pathlib import Path

import pytest

from darwin.future.data_objects.workflow import (
    WFUser,
)

test_data_path: Path = Path(__file__).parent / "data"
validate_json = test_data_path / "user.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_json.exists()
