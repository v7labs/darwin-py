from pathlib import Path
from typing import List
from uuid import uuid4

import orjson as json
import pytest

from darwin.future.core.client import ClientCore, DarwinConfig
from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.data_objects.item import ItemCore, ItemLayout, ItemSlot
from darwin.future.data_objects.properties import (
    FullProperty,
    PropertyValue,
    PropertyGranularity,
)
from darwin.future.data_objects.team import TeamCore, TeamMemberCore
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.data_objects.workflow import WorkflowCore


@pytest.fixture
def base_property_value() -> PropertyValue:
    return PropertyValue(
        id="0",
        position=0,
        type="string",
        value="test-value",
        color="rgba(0,0,0,0)",
    )


@pytest.fixture
def base_property_object(base_property_value: PropertyValue) -> FullProperty:
    return FullProperty(
        id="0",
        name="test-property",
        type="text",
        description="test-description",
        required=False,
        slug="test-property",
        team_id=0,
        annotation_class_id=0,
        property_values=[base_property_value],
        granularity=PropertyGranularity.section,
        options=[base_property_value],
    )


@pytest.fixture
def base_config() -> DarwinConfig:
    return DarwinConfig(
        api_key="test_key",
        base_url="http://test_url.com/",
        api_endpoint="http://test_url.com/api/",
        default_team="default-team",
        datasets_dir=Path("datasets"),
        teams={},
    )


@pytest.fixture
def items_json(item_core_list: List[ItemCore]) -> List[dict]:
    items: List[dict] = []
    for item in item_core_list:
        temp = dict(item)
        temp["id"] = str(temp["id"])
        temp["slots"] = [dict(slot) for slot in temp["slots"]]
        temp["layout"] = dict(temp["layout"])
        items.append(temp)
    return items


@pytest.fixture
def item_core_list() -> List[ItemCore]:
    items = []
    for i in range(5):
        slot = ItemSlot(slot_name=f"slot_{i}", file_name=f"file_{i}.jpg")
        layout = ItemLayout(slots=[f"slot_{i}"], type="grid", version=1)
        item = ItemCore(
            name=f"item_{i}",
            id=uuid4(),
            slots=[slot],
            dataset_id=i,
            processing_status="processed",
            layout=layout,
        )
        items.append(item)
    return items


@pytest.fixture
def base_client(base_config: DarwinConfig) -> ClientCore:
    return ClientCore(base_config)


@pytest.fixture
def base_team_json() -> dict:
    return {"slug": "test-team", "id": "0", "name": "test-team"}


@pytest.fixture
def base_team(base_team_json: dict) -> TeamCore:
    return TeamCore.model_validate(base_team_json)


@pytest.fixture
def base_item_json() -> dict:
    return {
        "name": "test-item",
        "id": "123e4567-e89b-12d3-a456-426655440000",
        "slots": [
            {"slot_name": "slot1", "file_name": "file1.jpg", "fps": 30},
            {"slot_name": "slot2", "file_name": "file2.jpg", "fps": 24},
        ],
        "path": "/",
        "archived": False,
        "priority": None,
        "tags": [],
        "layout": None,
    }


@pytest.fixture
def base_item_json_response() -> dict:
    return {
        "name": "test-item",
        "id": "123e4567-e89b-12d3-a456-426655440000",
        "slots": [
            {"slot_name": "slot1", "file_name": "file1.jpg", "fps": 1},
            {"slot_name": "slot2", "file_name": "file2.jpg", "fps": 1},
        ],
        "path": "/",
        "archived": False,
        "priority": None,
        "tags": [],
        "layout": None,
        "dataset_id": 101,
        "processing_status": "complete",
    }


@pytest.fixture
def base_items_json_response(base_item_json_response: dict) -> dict:
    return {"items": [base_item_json_response]}


@pytest.fixture
def base_item(base_item_json: dict) -> ItemCore:
    return ItemCore.model_validate(base_item_json)


@pytest.fixture
def base_workflow(base_single_workflow_object: dict) -> WorkflowCore:
    return WorkflowCore.model_validate(base_single_workflow_object)


@pytest.fixture
def base_team_member_json() -> dict:
    return {
        "email": "email",
        "id": "0",
        "first_name": "first",
        "last_name": "last",
        "role": "member",
        "team_id": "0",
        "user_id": "0",
    }


@pytest.fixture
def base_team_member(base_team_member_json: dict) -> TeamMemberCore:
    return TeamMemberCore.model_validate(base_team_member_json)


@pytest.fixture
def base_team_members_json(base_team_member_json: dict) -> List[dict]:
    members = []
    for item in TeamMemberRole:
        member_w_role = base_team_member_json.copy()
        member_w_role["role"] = item.value
        members.append(member_w_role)
    return members


@pytest.fixture
def team_members(base_team_members_json: List[dict]) -> List[TeamMemberCore]:
    return [TeamMemberCore.model_validate(item) for item in base_team_members_json]


@pytest.fixture
def base_dataset_json() -> dict:
    return {
        "name": "Test Dataset",
        "slug": "test-dataset",
        "id": "1",
        "releases": [],
    }


@pytest.fixture
def base_dataset_json_with_releases() -> dict:
    dataset = base_dataset_json()
    dataset["releases"] = [
        {"name": "release1"},
        {"name": "release2"},
    ]

    return dataset


@pytest.fixture
def base_dataset(base_dataset_json: dict) -> DatasetCore:
    return DatasetCore.model_validate(base_dataset_json)


def base_dataset_with_releases(base_dataset_json_with_releases: dict) -> DatasetCore:
    return DatasetCore.model_validate(base_dataset_json_with_releases)


@pytest.fixture
def base_datasets_json(base_dataset_json: dict) -> List[dict]:
    def transform_dataset(dataset_json_dict: dict, id: int) -> dict:
        dataset = dataset_json_dict.copy()

        dataset["id"] = id
        dataset["slug"] = f"{dataset['slug']}-{id}"
        dataset["name"] = f"{dataset['name']} {id}"

        return dataset

    # fmt: off
    return [
        transform_dataset(base_dataset_json, 1),
        transform_dataset(base_dataset_json, 2),
    ]
    # fmt: on


@pytest.fixture
def base_datasets_json_with_releases(base_dataset_json: dict) -> List[dict]:
    def transform_dataset(dataset_json_dict: dict, id: int) -> dict:
        dataset = dataset_json_dict.copy()

        dataset["id"] = id
        dataset["slug"] = f"{dataset['slug']}-{id}"
        dataset["name"] = f"{dataset['name']} {id}"
        dataset["releases"] = (
            [{"name": "release2"}] if id % 2 == 0 else [{"name": "release1"}]
        )

        return dataset

    # fmt: off
    return [
        transform_dataset(base_dataset_json, 1),
        transform_dataset(base_dataset_json, 2),
        transform_dataset(base_dataset_json, 3),
        transform_dataset(base_dataset_json, 4),
    ]
    # fmt: on


@pytest.fixture
def workflow_json() -> str:
    # fmt: off
    path = (
        Path(__file__).parent / 
        ".." / "data_objects" / 
        "workflow" / "data" / "workflow.json"
    ).resolve()
    # fmt: on
    assert path.exists()

    return path.read_bytes().decode("utf-8").replace("\n", "")


@pytest.fixture
def base_single_workflow_json(workflow_json: str) -> str:
    return f"[{workflow_json}]"


@pytest.fixture
def base_workflows_json(workflow_json: str) -> str:
    return f"[{workflow_json}, {workflow_json}, {workflow_json}]"


@pytest.fixture
def base_workflows_object(base_workflows_json: str) -> list:
    return json.loads(base_workflows_json)


@pytest.fixture
def base_single_workflow_object(base_workflows_object: dict) -> list:
    return base_workflows_object[0]


@pytest.fixture
def base_filterable_workflows() -> list:
    return [
        {
            "id": "6dca86a3-48fb-40cc-8594-88310f5f1fdf",
            "name": "test-workflow-1",
            "team_id": "100",
            "inserted_at": "2021-06-01T15:00:00.000+00:00",
            "updated_at": "2021-06-05T15:00:00.000+00:00",
            "dataset": {
                "id": 1,
                "name": "test-dataset-1",
                "instructions": "test-instructions-1",
            },
            "stages": [
                {
                    "id": "53d2c997-6bb0-4766-803c-3c8d1fb21072",
                    "name": "stage-1",
                    "type": "annotate",
                    "assignable_users": [
                        {
                            "stage_id": "d96a4865-f7d1-466a-abc6-5a61b2339c16",
                            "user_id": "1",
                        },
                        {
                            "stage_id": "70adf8be-d6b5-4f54-9d99-ecf1c6959442",
                            "user_id": "2",
                        },
                    ],
                    "edges": [
                        {
                            "id": "5e858c07-28d7-48b5-a7a3-4697f3212d7c",
                            "name": "edge-1",
                            "source_stage_id": None,
                            "target_stage_id": "6aeb1b33-9234-4d00-95e7-97b8e477ee02",
                        },
                        {
                            "id": "6aeb1b33-9234-4d00-95e7-97b8e477ee02",
                            "name": "edge-2",
                            "source_stage_id": "5e858c07-28d7-48b5-a7a3-4697f3212d7c",
                            "target_stage_id": "32151eaf-edbd-4703-9049-50803f1df2bf",
                        },
                        {
                            "id": "9b527a3d-c765-42fd-88b6-594f5b411c07",
                            "name": "edge-3",
                            "source_stage_id": "6aeb1b33-9234-4d00-95e7-97b8e477ee02",
                            "target_stage_id": None,
                        },
                    ],
                }
            ],
            "thumbnails": [
                "https://0.0.0.0/thumbnails/1.png",
                "https://0.0.0.0/thumbnails/2.png",
                "https://0.0.0.0/thumbnails/3.png",
            ],
        },
        {
            "id": "e34fe935-4a1c-4231-bb55-454e2ac7673f",
            "name": "test-workflow-2",
            "team_id": "100",
            "inserted_at": "2021-06-03T15:00:00.000+00:00",
            "updated_at": "2021-06-05T15:00:00.000+00:00",
            "dataset": {
                "id": 2,
                "name": "test-dataset-2",
                "instructions": "test-instructions-1",
            },
            "stages": [
                {
                    "id": "aabd5e3a-4ccd-4cc3-8cc1-c8455972c101",
                    "name": "stage-1",
                    "type": "annotate",
                    "assignable_users": [
                        {
                            "stage_id": "d96a4865-f7d1-466a-abc6-5a61b2339c16",
                            "user_id": "1",
                        },
                        {
                            "stage_id": "70adf8be-d6b5-4f54-9d99-ecf1c6959442",
                            "user_id": "2",
                        },
                    ],
                    "edges": [
                        {
                            "id": "42c53da7-e3f2-4c81-bec7-449439cef694",
                            "name": "edge-1",
                            "source_stage_id": None,
                            "target_stage_id": "b5da9e56-4bf4-4a00-826d-741d1febd3da",
                        },
                        {
                            "id": "8ea42761-8971-4be1-b359-66fc878a807b",
                            "name": "edge-2",
                            "source_stage_id": "b5da9e56-4bf4-4a00-826d-741d1febd3da",
                            "target_stage_id": "2a3d8f47-dba6-4fdb-88e0-beb4b2a5ed24",
                        },
                        {
                            "id": "2a3d8f47-dba6-4fdb-88e0-beb4b2a5ed24",
                            "name": "edge-3",
                            "source_stage_id": "8ea42761-8971-4be1-b359-66fc878a807b",
                            "target_stage_id": None,
                        },
                    ],
                }
            ],
            "thumbnails": [
                "https://0.0.0.0/thumbnails/4.png",
                "https://0.0.0.0/thumbnails/5.png",
                "https://0.0.0.0/thumbnails/6.png",
            ],
        },
        {
            "id": "45cf0abe-58a2-4878-b171-4fb5421a1c39",
            "name": "test-workflow-3",
            "team_id": "100",
            "inserted_at": "2021-06-05T15:00:00.000+00:00",
            "updated_at": "2021-06-10T15:00:00.000+00:00",
            "dataset": {
                "id": 3,
                "name": "test-dataset-3",
                "instructions": "test-instructions-1",
            },
            "stages": [
                {
                    "id": "5445adcb-193d-4f76-adb0-0c6d5f5e4c04",
                    "name": "stage-1",
                    "type": "annotate",
                    "assignable_users": [
                        {
                            "stage_id": "16d390ad-2a6b-4232-8434-0489e9533afd",
                            "user_id": "1",
                        },
                        {
                            "stage_id": "f9816ea0-4bcf-4293-a399-3d35770db59e",
                            "user_id": "2",
                        },
                    ],
                    "edges": [
                        {
                            "id": "7dc64300-dc1b-42f3-825f-de09ece4ed6f",
                            "name": "edge-1",
                            "source_stage_id": None,
                            "target_stage_id": "d7510016-5286-4f72-a13c-e350fefb652b",
                        },
                        {
                            "id": "d7510016-5286-4f72-a13c-e350fefb652b",
                            "name": "edge-2",
                            "source_stage_id": "7dc64300-dc1b-42f3-825f-de09ece4ed6f",
                            "target_stage_id": "7233d3e4-ac01-4598-aada-1fc73e6fc518",
                        },
                        {
                            "id": "7233d3e4-ac01-4598-aada-1fc73e6fc518",
                            "name": "edge-3",
                            "source_stage_id": "d7510016-5286-4f72-a13c-e350fefb652b",
                            "target_stage_id": None,
                        },
                    ],
                }
            ],
            "thumbnails": [
                "https://0.0.0.0/thumbnails/7.png",
                "https://0.0.0.0/thumbnails/8.png",
                "https://0.0.0.0/thumbnails/9.png",
            ],
        },
    ]
