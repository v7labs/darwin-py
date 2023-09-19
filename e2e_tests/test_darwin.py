import re
import tempfile
import uuid
from pathlib import Path
from typing import Generator

import pytest

from e2e_tests.helpers import run_cli_command
from e2e_tests.objects import E2EDataset
from e2e_tests.setup_tests import create_random_image


@pytest.fixture
def new_dataset() -> E2EDataset:
    """Create a new dataset via darwin cli and return the dataset object, complete with teardown"""
    uuid_str = str(uuid.uuid4())
    new_dataset_name = "test_dataset_" + uuid_str
    result = run_cli_command(f"darwin dataset create {new_dataset_name}")
    assert result[0] == 0
    id_raw = re.findall(r"datasets[/\\+](\d+)", result[1])
    assert id_raw is not None and len(id_raw) == 1
    id = int(id_raw[0])
    teardown_dataset = E2EDataset(id, new_dataset_name, None)

    # Add the teardown dataset to the pytest object to ensure it gets deleted when pytest is done
    pytest.datasets.append(teardown_dataset)  # type: ignore
    return teardown_dataset


@pytest.fixture
def local_dataset(new_dataset: E2EDataset) -> Generator[E2EDataset, None, None]:
    with tempfile.TemporaryDirectory() as temp_directory:
        new_dataset.directory = temp_directory
        yield new_dataset


@pytest.fixture
def local_dataset_with_images(local_dataset: E2EDataset) -> E2EDataset:
    assert local_dataset.directory is not None
    [create_random_image(local_dataset.slug, Path(local_dataset.directory)) for x in range(3)]
    return local_dataset


def test_darwin_create(local_dataset: E2EDataset) -> None:
    """
    Test creating a dataset via the darwin cli, heavy lifting performed
    by the fixture which already creates a dataset and adds it to the pytest object via cli
    """
    assert local_dataset.id is not None
    assert local_dataset.name is not None


def test_darwin_push(local_dataset_with_images: E2EDataset) -> None:
    """
    Test pushing a dataset via the darwin cli, dataset created via fixture with images added to object
    """
    assert local_dataset_with_images.id is not None
    assert local_dataset_with_images.name is not None
    assert local_dataset_with_images.directory is not None
    result = run_cli_command(
        f"darwin dataset push {local_dataset_with_images.name} {local_dataset_with_images.directory}"
    )
    assert result[0] == 0


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
