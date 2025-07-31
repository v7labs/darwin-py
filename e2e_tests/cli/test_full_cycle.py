import os
import shutil
import time
from pathlib import Path

from e2e_tests.helpers import (
    SERVER_WAIT_TIME,
    assert_cli,
    run_cli_command,
    export_release,
)
from e2e_tests.objects import E2EDataset, ConfigValues
from e2e_tests.cli.test_import import compare_annotations_export
from e2e_tests.cli.test_push import extract_and_push


def copy_files_to_flat_directory(source_dir, target_dir):
    """
    Multi-source file items are pulled in a structure where every file is contained in a
    folder named after the slot it's in. Multi-file push only considers files in the
    top-level of the passed directory, so to push pulled multi-file items as multi-file
    items, we need to copy the files into a flat directory
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".jpg"):
                shutil.copy(
                    os.path.join(root, file),
                    os.path.join(target_dir, file),
                )


def test_full_cycle_images(
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


def test_full_cycle_nifti(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
):
    """
    This test performs the following steps:
    - 1: Registers a set of DICOM files from external storage to a dataset
    - 2: Imports mask annotations
    - 3: Creates and pulls a release of the dataset
    - 4: Deletes all items from the dataset
    - 5: Pushes and imports the pulled files & annotations to the dataset
    - 6: Deletes locally pulled copies of the dataset files
    - 7: Creates and pulls a new release of the dataset
    - 8: Assert that the pulled data is as expected

    It is designed to catch errors that may arise from changes to exported Darwin JSON
    """
    item_type = "multi_segment_nifti"
    annotation_format = "darwin"
    first_release_name = "first_release"
    second_release_name = "second_release"
    pull_dir = Path(
        f"{Path.home()}/.darwin/datasets/{config_values.team_slug}/{local_dataset.slug}"
    )
    annotations_import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "nifti_multi_segment"
    )
    source_files = [
        "axial_RPI_pixdim_1.0_1.0_1.0",
        "coronal_LAS_pixdim_0.1_0.2_0.5",
        "sagittal_LPI_pixdim_0.1_0.2_0.5",
    ]

    expected_filepaths = [f"{pull_dir}/images/{file}.dcm" for file in source_files]

    # Populate the dataset with items and annotations
    local_dataset.register_read_only_items(config_values, item_type)
    time.sleep(SERVER_WAIT_TIME)

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
    # we are uploading 3 DICOM images which need to be extracted asynchronously
    time.sleep(SERVER_WAIT_TIME * 3)

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


def test_full_cycle_video(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
):
    """
    This test performs the following steps:
    - 1: Pushes a video to the dataset
    - 2: Imports some annotations
    - 3: Creates and pulls a release of the dataset
    - 4: Deletes all items from the dataset
    - 5: Pushes and imports the pulled files & annotations to the dataset
    - 6: Deletes locally pulled copies of the dataset files
    - 7: Creates and pulls a new release of the dataset
    - 8: Assert that the pulled data is as expected

    It is designed to catch errors that may arise from changes to exported Darwin JSON
    """
    item_type = "single_slotted_video"
    annotation_format = "darwin"
    first_release_name = "first_release"
    second_release_name = "second_release"
    zipped_video_dir = "25_frame_video"
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{zipped_video_dir}.zip"
    pull_dir = Path(
        f"{Path.home()}/.darwin/datasets/{config_values.team_slug}/{local_dataset.slug}"
    )
    annotations_import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "video_annotations_small_video"
    )
    expected_filepaths = [
        f"{pull_dir}/images/small_video.mp4",
    ]

    # Push a video to the dataset
    extract_and_push(push_dir, local_dataset, config_values, zipped_video_dir)

    # Upload annotations to the dataset
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


def test_full_cycle_multi_slotted_item(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
):
    """
    This test performs the following steps:
    - 1: Registers a multi-slotted item from external storage to a dataset
    - 2: Imports some annotations
    - 3: Creates and pulls a release of the dataset
    - 4: Deletes all items from the dataset
    - 5: Pushes and imports the pulled files & annotations to the dataset
    - 6: Deletes locally pulled copies of the dataset files
    - 7: Creates and pulls a new release of the dataset
    - 8: Assert that the pulled data is as expected

    It is designed to catch errors that may arise from changes to exported Darwin JSON
    """
    item_type = "multi_slotted"
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
        / "multi_slotted_annotations_with_slots_defined"
    )
    expected_filepaths = [
        f"{pull_dir}/images/multi_slotted_item/0/image_1.jpg",
        f"{pull_dir}/images/multi_slotted_item/1/image_2.jpg",
        f"{pull_dir}/images/multi_slotted_item/2/image_3.jpg",
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

    # Create a temporary directory for pushing files
    tmp_push_dir = f"{pull_dir}/multi_slotted_item"
    copy_files_to_flat_directory(f"{pull_dir}/images", tmp_push_dir)

    # Push and import the pulled files and annotations to the dataset
    result = run_cli_command(
        f"darwin dataset push {local_dataset.name} {tmp_push_dir} --item-merge-mode slots"
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


def test_full_cycle_multi_channel_item(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
):
    """
    This test performs the following steps:
    - 1: Registers a multi-channel from external storage item to the dataset
    - 2: Imports some annotations
    - 3: Creates and pulls a release of the dataset
    - 4: Deletes all items from the dataset
    - 5: Pushes and imports the pulled files & annotations to the dataset
    - 6: Deletes locally pulled copies of the dataset files
    - 7: Creates and pulls a new release of the dataset
    - 8: Assert that the pulled data is as expected

    It is designed to catch errors that may arise from changes to exported Darwin JSON
    """
    item_type = "multi_channel"
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
        / "multi_channel_annotations_with_slots_defined"
    )
    expected_filepaths = [
        f"{pull_dir}/images/multi_channel_item/image_1.jpg/image_1.jpg",
        f"{pull_dir}/images/multi_channel_item/image_2.jpg/image_2.jpg",
        f"{pull_dir}/images/multi_channel_item/image_3.jpg/image_3.jpg",
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

    # Create a temporary directory for pushing files
    tmp_push_dir = f"{pull_dir}/multi_channel_item"
    copy_files_to_flat_directory(f"{pull_dir}/images", tmp_push_dir)

    # Push and import the pulled files and annotations to the dataset
    result = run_cli_command(
        f"darwin dataset push {local_dataset.name} {tmp_push_dir} --item-merge-mode channels"
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
        base_slot="image_1.jpg",
        unzip=False,
    )
