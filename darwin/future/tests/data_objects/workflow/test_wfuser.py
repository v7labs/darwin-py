from pathlib import Path

import pytest

from darwin.future.data_objects.workflow import WFUser

test_data_path: Path = Path(__file__).parent / "data"
validate_json = test_data_path / "user.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_json.exists()


def test_WFUser_validates_from_valid_json() -> None:
    parsed_user = WFUser.parse_file(validate_json)

    assert isinstance(parsed_user, WFUser)
    assert parsed_user.user_id == 100
    assert str(parsed_user.stage_id) == "0fa1ae43-fb46-44d7-bf85-b78e81d0d02f"
