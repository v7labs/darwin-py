import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Generator

import pytest

from e2e_tests.helpers import (  # noqa: F401
    api_call,
    assert_cli,
    create_random_image,
    run_cli_command,
)
from e2e_tests.objects import ConfigValues, E2EDataset, E2EItem, TeamConfigValues


@pytest.fixture
def local_dataset(
    new_dataset: E2EDataset,  # noqa: F811
) -> Generator[E2EDataset, None, None]:
    with tempfile.TemporaryDirectory() as temp_directory:
        new_dataset.directory = temp_directory
        yield new_dataset


@pytest.fixture
def local_dataset_with_images(local_dataset: E2EDataset) -> E2EDataset:
    assert local_dataset.directory is not None
    for x in range(3):
        path = create_random_image(
            str(x), Path(local_dataset.directory), fixed_name=True
        )
        local_dataset.add_item(
            E2EItem(
                name=path.name,
                id=uuid.uuid4(),  # random uuid as only need item for annotation later
                path=str(path),
                file_name=path.name,
                slot_name="",
                annotations=[],
            )
        )
    return local_dataset


def basic_annotation(name: str) -> dict:
    base_annotation_path = Path(__file__).parent / "data" / "base_annotation.json"
    with open(base_annotation_path, "r") as f:
        annotation = json.load(f)
    annotation["item"]["name"] = name
    return annotation


@pytest.fixture
def local_dataset_with_annotations(local_dataset_with_images: E2EDataset) -> E2EDataset:
    assert local_dataset_with_images.directory is not None
    dir = Path(local_dataset_with_images.directory) / "annotations"
    os.mkdir(dir)
    for item in local_dataset_with_images.items:
        annotation = basic_annotation(item.name)
        filename = dir / f"{item.name[:-4]}.json"
        with open(filename, "w") as f:
            json.dump(annotation, f)
    return local_dataset_with_images


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
    assert_cli(result, 0)


def test_darwin_import(local_dataset_with_annotations: E2EDataset) -> None:
    """
    Test importing a dataset via the darwin cli, dataset created via fixture with annotations added to objects
    """
    assert local_dataset_with_annotations.id is not None
    assert local_dataset_with_annotations.name is not None
    assert local_dataset_with_annotations.directory is not None
    result = run_cli_command(
        f"darwin dataset push {local_dataset_with_annotations.name} {local_dataset_with_annotations.directory}"
    )
    assert_cli(result, 0)
    result = run_cli_command(
        f"darwin dataset import {local_dataset_with_annotations.name} darwin {Path(local_dataset_with_annotations.directory) / 'annotations'} --yes",
    )
    assert_cli(result, 0)


def test_darwin_export(
    isolated_team: TeamConfigValues,
    config_values: ConfigValues,
    local_dataset_with_annotations: E2EDataset,
) -> None:
    """
    Test exporting a dataset via the darwin cli, dataset created via fixture with annotations added to objects.
    """

    assert local_dataset_with_annotations.id is not None
    assert local_dataset_with_annotations.name is not None
    assert local_dataset_with_annotations.directory is not None

    result = run_cli_command(
        f"darwin team {isolated_team.team_slug} && darwin dataset push {local_dataset_with_annotations.name} {local_dataset_with_annotations.directory}"
    )
    assert_cli(result, 0)

    result = run_cli_command(
        f"darwin team {isolated_team.team_slug} && darwin dataset import {local_dataset_with_annotations.name} darwin {Path(local_dataset_with_annotations.directory) / 'annotations'} --yes",
    )
    assert_cli(result, 0)

    # Get class ids as export either needs a workflow and complete annotations or the class ids
    url = f"{config_values.server}/api/teams/{isolated_team.team_slug}/annotation_classes?include_tags=true"
    response = api_call("get", url, None, isolated_team.api_key)
    if not response.ok:
        raise Exception(f"Failed to get annotation classes: {response.text}")

    classes = response.json()["annotation_classes"]
    class_ids = [c["id"] for c in classes]
    class_str = " ".join([str(c) for c in class_ids])

    result = run_cli_command(
        f"darwin team {isolated_team.team_slug} && darwin dataset export {local_dataset_with_annotations.name} test_darwin_export --class-ids {class_str}"
    )
    assert_cli(result, 0, in_stdout="successfully exported")

    result = run_cli_command(
        f"darwin team {isolated_team.team_slug} && darwin dataset releases {local_dataset_with_annotations.name}"
    )
    assert_cli(
        result, 0, in_stdout="No available releases, export one first", inverse=True
    )


def test_delete(local_dataset: E2EDataset) -> None:
    """
    Test deleting a dataset via the darwin cli, dataset created via fixture
    """
    assert local_dataset.id is not None
    assert local_dataset.name is not None
    result = run_cli_command(f"yes Y | darwin dataset remove {local_dataset.name}")
    assert_cli(result, 0)
    # Check that the dataset is gone
    result = run_cli_command(f"darwin dataset files {local_dataset.name}")
    assert_cli(result, 1, in_stdout="Error: No dataset with")


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
