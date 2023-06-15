from pathlib import Path
from typing import List

import pytest

from darwin.future.core.client import Client, DarwinConfig
from darwin.future.data_objects.dataset import Dataset
from darwin.future.data_objects.team import Team, TeamMember
from darwin.future.data_objects.team_member_role import TeamMemberRole


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
def base_client(base_config: DarwinConfig) -> Client:
    return Client(base_config)


@pytest.fixture
def base_team_json() -> dict:
    return {"slug": "test-team", "id": "0"}


@pytest.fixture
def base_team(base_team_json: dict) -> Team:
    return Team.parse_obj(base_team_json)


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
def base_team_member(base_team_member_json: dict) -> TeamMember:
    return TeamMember.parse_obj(base_team_member_json)


@pytest.fixture
def base_team_members_json(base_team_member_json: dict) -> List[dict]:
    members = []
    for item in TeamMemberRole:
        member_w_role = base_team_member_json.copy()
        member_w_role["role"] = item.value
        members.append(member_w_role)
    return members


@pytest.fixture
def team_members(base_team_members_json: List[dict]) -> List[TeamMember]:
    return [TeamMember.parse_obj(item) for item in base_team_members_json]


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
def base_dataset(base_dataset_json: dict) -> Dataset:
    return Dataset.parse_obj(base_dataset_json)


def base_dataset_with_releases(base_dataset_json_with_releases: dict) -> Dataset:
    return Dataset.parse_obj(base_dataset_json_with_releases)


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
        dataset["releases"] = [{"name": "release2"}] if id % 2 == 0 else [{"name": "release1"}]

        return dataset

    # fmt: off
    return [
        transform_dataset(base_dataset_json, 1),
        transform_dataset(base_dataset_json, 2),
        transform_dataset(base_dataset_json, 3),
        transform_dataset(base_dataset_json, 4),
    ]
    # fmt: on
