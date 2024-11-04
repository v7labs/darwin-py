import shutil
from pathlib import Path

from e2e_tests.helpers import assert_cli, run_cli_command, export_release
from e2e_tests.objects import E2EDataset, ConfigValues
from e2e_tests.cli.test_import import compare_annotations_export


def test_full_cycle(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
):
    """
    This test performs the following steps:
    - 1: Registers a set of files from external storage to a dataset
    - 2: Imports some annotations
    - 3: Creates and pulls a release of the dataset
    - 4: Deletes all items from the dataset
    - 5: Pushes and imports the pulled files & annotations to the dataset
    - 6: Deletes locally pulled copies of the dataset files
    - 7: Creates and pulls a new release of the dataset
    - 8: Assert that the pulled data is as expected

    It is designed to catch errors that may arise from changes to exported Darwin JSON
    """
    item_type = "single_slotted"
    annotation_format = "darwin"
    first_release_name = "first_release"
    second_release_name = "second_release"
    pull_dir = Path(
        f"{Path.home()}/.darwin/datasets/{config_values.team_slug}/{local_dataset.slug}"
    )
    annotations_import_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_with_item_level_properties"
    )
    expected_filepaths = [
        f"{pull_dir}/images/image_1.jpg",
        f"{pull_dir}/images/image_2.jpg",
        f"{pull_dir}/images/dir1/image_3.jpg",
        f"{pull_dir}/images/dir1/image_4.jpg",
        f"{pull_dir}/images/dir2/image_5.jpg",
        f"{pull_dir}/images/dir2/image_6.jpg",
        f"{pull_dir}/images/dir1/dir3/image_7.jpg",
        f"{pull_dir}/images/dir1/dir3/image_8.jpg",
    ]

    # Populate the dataset with items and annotations
    local_dataset.register_read_only_items(config_values, item_type)
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} {annotation_format} {annotations_import_dir}"
    )
    assert_cli(result, 0)

    # Pull a first release of the dataset
    original_release = export_release(
        annotation_format, local_dataset, config_values, release_name=first_release_name
    )
    result = run_cli_command(
        f"darwin dataset pull {local_dataset.name}:{original_release.name}"
    )
    assert_cli(result, 0)

    # Delete all items in the dataset
    local_dataset.delete_items(config_values)

    # Push and import the pulled files and annotations to the dataset
    result = run_cli_command(
        f"darwin dataset push {local_dataset.name} {pull_dir}/images --preserve-folders"
    )
    assert_cli(result, 0)
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} {annotation_format} {pull_dir}/releases/{first_release_name}/annotations"
    )
    assert_cli(result, 0)

    # Delete local copies of the dataset files for the dataset
    shutil.rmtree(f"{pull_dir}/images")

    # Pull a second release of the dataset
    new_release = export_release(
        annotation_format,
        local_dataset,
        config_values,
        release_name=second_release_name,
    )
    result = run_cli_command(
        f"darwin dataset pull {local_dataset.name}:{new_release.name}"
    )
    assert_cli(result, 0)

    # Check that all expected files have been downloaded
    all_filepaths = list(pull_dir.rglob("*"))
    for expected_file in expected_filepaths:
        assert Path(expected_file) in all_filepaths

    # Check that all downloaded annotations are as expected
    compare_annotations_export(
        Path(f"{pull_dir}/releases/{first_release_name}/annotations"),
        Path(f"{pull_dir}/releases/{second_release_name}/annotations"),
        item_type,
        unzip=False,
    )
