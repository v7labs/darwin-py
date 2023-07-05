import pytest

from darwin.item import DatasetItem


@pytest.fixture
def response_json_slots() -> dict:
    return {
        "id": "test_id",
        "name": "test_filename",
        "path": "test_path",
        "status": "test_status",
        "archived": "test_archived",
        "dataset_id": "test_dataset_id",
        "dataset_slug": "test_dataset_slug",
        "seq": None,
        "workflow_data": {"workflow_id": "test_workflow_id"},
        "workflow_status": "test_workflow_status",
        "slots": [{"size_bytes": 1, "path": "test_path"}],
    }


def test_item_parse_w_slots(response_json_slots: dict) -> None:
    item = DatasetItem.parse(response_json_slots, "test_dataset_slug")
    assert item.id == response_json_slots["id"]
    assert item.filename == response_json_slots["name"]
    assert item.path == response_json_slots["path"]
    assert item.status == response_json_slots["status"]
    assert item.archived == response_json_slots["archived"]
    assert item.dataset_id == response_json_slots["dataset_id"]
    assert item.dataset_slug == "test_dataset_slug"
    assert item.seq == response_json_slots["seq"]
    assert item.current_workflow_id == response_json_slots["workflow_data"]["workflow_id"]
    assert item.current_workflow == response_json_slots["workflow_data"]
    assert item.slots == response_json_slots["slots"]
