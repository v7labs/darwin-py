import pytest
from pydantic import BaseModel, ValidationError

from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.data_objects.release import ReleaseCore
from darwin.future.data_objects.team import TeamCore
from darwin.future.tests.data_objects.fixtures import *


def test_integrated_parsing_works_with_raw(basic_combined: dict) -> None:
    team = TeamCore.model_validate(basic_combined)
    assert team.slug == "test-team"
    assert team.datasets is not None
    assert team.datasets[0].name == "test-dataset"
    assert team.datasets[0].releases is not None
    assert team.datasets[0].releases[0].name == "test-release"


def test_broken_obj_raises(broken_combined: dict) -> None:
    with pytest.raises(ValidationError):
        TeamCore.model_validate(broken_combined)


@pytest.mark.parametrize("test_object", [TeamCore, DatasetCore, ReleaseCore])
def test_empty_obj_raises(test_object: BaseModel) -> None:
    with pytest.raises(ValidationError):
        test_object.model_validate({})
