from pathlib import Path

from darwin.future.data_objects.workflow import WFEdgeCore

test_data_path: Path = Path(__file__).parent / "data"
validate_json = test_data_path / "edge.json"


def test_file_exists() -> None:
    # This is a test sanity check to make sure the file exists
    # Helps avoids headaches when debugging tests
    assert validate_json.exists()


def test_WFEdge_validates_from_valid_json() -> None:
    parsed_edge = WFEdgeCore.parse_file(validate_json)

    assert isinstance(parsed_edge, WFEdgeCore)
