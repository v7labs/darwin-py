import unittest

import pytest
from pydantic import BaseModel, ValidationError

from darwin.future.data_objects.darwin_meta import Dataset, Release, Team


@pytest.fixture
def basic_team() -> dict:
    return {"slug": "test-team", "id": 0}


@pytest.fixture
def basic_dataset() -> dict:
    return {"name": "test-dataset", "slug": "test-dataset"}


@pytest.fixture
def basic_release() -> dict:
    return {"name": "test-release"}


@pytest.fixture
def basic_combined(basic_team: dict, basic_dataset: dict, basic_release: dict) -> dict:
    combined = basic_team
    combined["datasets"] = [basic_dataset]
    combined["datasets"][0]["releases"] = [basic_release]
    return combined


@pytest.fixture
def broken_combined(basic_combined: dict) -> dict:
    del basic_combined["datasets"][0]["name"]
    return basic_combined


def test_integrated_parsing_works_with_raw(basic_combined: dict) -> None:
    team = Team.parse_obj(basic_combined)
    assert team.slug == "test-team"
    assert team.datasets is not None
    assert team.datasets[0].name == "test-dataset"
    assert team.datasets[0].releases is not None
    assert team.datasets[0].releases[0].name == "test-release"


def test_broken_obj_raises(broken_combined: dict) -> None:
    with pytest.raises(ValidationError) as e_info:
        broken = Team.parse_obj(broken_combined)


@pytest.mark.parametrize("test_object", [Team, Dataset, Release])
def test_empty_obj_raises(test_object: BaseModel) -> None:
    with pytest.raises(ValidationError) as e_info:
        broken = test_object.parse_obj({})
