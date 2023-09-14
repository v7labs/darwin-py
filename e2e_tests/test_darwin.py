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
    uuid_str = str(uuid.uuid4())
    new_dataset_name = "test_dataset_" + uuid_str
    result = run_cli_command(f"darwin dataset create {new_dataset_name}")
    assert result[0] == 0
    id_raw = re.search(r"/datasets/(\d+)", result[1])
    assert id_raw is not None
    id = int(id_raw.group(1))
    teardown_dataset = E2EDataset(id, new_dataset_name, None)
    pytest.datasets.append(teardown_dataset) # type: ignore
    return teardown_dataset

@pytest.fixture
def local_dataset(new_dataset: E2EDataset) -> Generator[E2EDataset, None, None]:
    with tempfile.TemporaryDirectory() as temp_directory:
        new_dataset.directory = temp_directory
        yield new_dataset

@pytest.fixture
def local_dataset_with_images(local_dataset: E2EDataset) -> Generator[E2EDataset, None, None]:
    assert local_dataset.directory is not None
    [create_random_image(local_dataset.slug, Path(local_dataset.directory)) for x in range(3)]
    yield local_dataset


def test_darwin_create(local_dataset: E2EDataset) -> None:
    assert local_dataset.id is not None
    assert local_dataset.name is not None

    


def test_darwin_push(local_dataset_with_images: E2EDataset) -> None:
    assert local_dataset_with_images.id is not None
    assert local_dataset_with_images.name is not None
    assert local_dataset_with_images.directory is not None
    result = run_cli_command(f"darwin dataset push {local_dataset_with_images.name} {local_dataset_with_images.directory}")
    assert result[0] == 0

    

    

# def test_darwin_import() -> None:
#     uuid_str = str(uuid.uuid4())
#     new_dataset_name = "test_dataset_" + uuid_str
#     result = run_cli_command(f"darwin dataset create {new_dataset_name}")
#     assert result[0] == 0
#     assert "has been created" in result[1]
#     id_raw = re.search(r"/datasets/(\d+)", result[1])
#     assert id_raw is not None
#     id = int(id_raw.group(1))

#     with tempfile.TemporaryDirectory() as temp_directory:
#         images = [create_random_image(uuid_str, Path(temp_directory)) for x in range(5)]
#         result = run_cli_command(f"darwin dataset push {new_dataset_name} {temp_directory}")
#         assert result[0] == 0

#     result = run_cli_command(f"yes Y | darwin dataset remove {new_dataset_name}")
#     assert result[0] == 0

if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])

    