from typing import List
from uuid import UUID, uuid4

import pytest

from darwin.future.data_objects.item import Folder, ItemCore, ItemLayout


@pytest.fixture
def base_layout() -> ItemLayout:
    return ItemLayout(
        slots=["slot1", "slot2"], type="grid", layout_shape=[2, 1], version=2
    )


@pytest.fixture
def base_items() -> List[ItemCore]:
    return [
        ItemCore(
            name=f"test_{i}",
            path="test_path",
            dataset_id=1,
            id=UUID("00000000-0000-0000-0000-000000000000"),
            slots=[],
            processing_status="complete",
            priority=0,
        )
        for i in range(10)
    ]


@pytest.fixture
def base_folders() -> List[Folder]:
    return [
        Folder(
            dataset_id=0,
            filtered_item_count=1,
            path=f"test_path_{i}",
            unfiltered_item_count=1,
        )
        for i in range(10)
    ]


@pytest.fixture
def base_items_json(base_items: List[ItemCore]) -> List[dict]:
    items = [item.model_dump() for item in base_items]
    # json library doesn't support UUIDs so need to be str'd
    for item in items:
        item["id"] = str(item["id"])
    return items


@pytest.fixture
def base_folders_json(base_folders: List[Folder]) -> List[dict]:
    return [folder.model_dump() for folder in base_folders]


@pytest.fixture
def UUIDs() -> List[UUID]:
    return [uuid4() for i in range(10)]


@pytest.fixture
def UUIDs_str(UUIDs: List[UUID]) -> List[str]:
    return [str(uuid) for uuid in UUIDs]


@pytest.fixture
def stage_id() -> UUID:
    return uuid4()


@pytest.fixture
def workflow_id() -> UUID:
    return uuid4()
