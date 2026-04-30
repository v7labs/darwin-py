import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from darwin.path_utils import parse_metadata
from e2e_tests.helpers import (
    assert_cli,
    run_cli_command,
    export_release,
    wait_until_items_processed,
)
from e2e_tests.objects import E2EDataset, ConfigValues
from e2e_tests.cli.test_import import compare_annotations_export
from e2e_tests.cli.test_push import extract_and_push


def _flatten_properties_with_parents(
    metadata: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Collapses a parsed ``metadata.json`` into a flat list of property
    definitions across class-level and item-level, keyed by ``name`` so we
    can cross-reference them between exports without relying on server-side
    IDs (which are regenerated on each import).
    """
    flat: List[Dict[str, Any]] = []
    for klass in metadata.get("classes", []):
        for prop in klass.get("properties", []):
            flat.append({"class": klass["name"], **prop})
    for prop in metadata.get("properties", []):
        flat.append({"class": None, **prop})
    return flat


def assert_nested_metadata_round_trips(
    first_metadata_path: Path, second_metadata_path: Path
) -> None:
    """
    Asserts that class-level and item-level nested property metadata are
    preserved across a push/pull round-trip. Every nested child in the first
    export must also be nested in the second export with the same
    ``parent_name`` and a matching trigger condition (``type`` plus, for
    ``value_match``, the set of referenced parent value names).
    """
    first_flat = _flatten_properties_with_parents(parse_metadata(first_metadata_path))
    second_flat = _flatten_properties_with_parents(parse_metadata(second_metadata_path))

    # ``(class, name) -> property`` lookup lets us cross-reference properties
    # across exports by their semantic identity (name), consistent with how
    # darwin-py identifies properties everywhere else.
    second_by_key = {(p["class"], p["name"]): p for p in second_flat}

    nested_children_first = [p for p in first_flat if p.get("parent_name") is not None]
    assert nested_children_first, (
        "Test setup error: first metadata export does not contain any nested "
        "property (parent_name). The fixture must include at least one "
        "nested property to make this assertion meaningful."
    )

    for child in nested_children_first:
        key = (child["class"], child["name"])
        assert (
            key in second_by_key
        ), f"Nested child property '{child['name']}' missing from second export"
        second_child = second_by_key[key]

        assert second_child.get("parent_name") == child["parent_name"], (
            f"Child '{child['name']}' lost or changed its parent_name "
            f"on round-trip: {child['parent_name']!r} -> "
            f"{second_child.get('parent_name')!r}"
        )

        first_trigger = child.get("trigger_condition") or {}
        second_trigger = second_child.get("trigger_condition") or {}
        assert first_trigger.get("type") == second_trigger.get(
            "type"
        ), f"Trigger type of '{child['name']}' changed on round-trip"
        if first_trigger.get("type") == "value_match":
            assert set(first_trigger.get("values") or []) == set(
                second_trigger.get("values") or []
            ), (
                f"value_match trigger values for '{child['name']}' changed "
                "on round-trip"
            )


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
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)
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
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)

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
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)

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
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)
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
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)
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
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)
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


def test_full_cycle_nested_properties(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
):
    """
    Full round-trip for nested properties at all three granularities.

    Steps:
    - 1: Registers files from external storage to a dataset
    - 2: Imports annotations and metadata.json that declare a nested property
         hierarchy at item, section, and annotation granularity (with children
         deliberately listed before their parents in metadata.json to exercise
         the importer's topological sort).
    - 3: Creates and pulls a first release
    - 4: Deletes all items
    - 5: Re-pushes the pulled files and re-imports from the pulled release
    - 6: Creates and pulls a second release
    - 7: Asserts annotation + item property values survive the round-trip
         (via compare_annotations_export) and that metadata.json nesting
         structure (parent_property_id + trigger_condition) is preserved
         across exports (via assert_nested_metadata_round_trips).
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
        / "image_annotations_with_nested_properties"
    )

    local_dataset.register_read_only_items(config_values, item_type)
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} {annotation_format} {annotations_import_dir}"
    )
    assert_cli(result, 0)

    original_release = export_release(
        annotation_format, local_dataset, config_values, release_name=first_release_name
    )
    result = run_cli_command(
        f"darwin dataset pull {local_dataset.name}:{original_release.name}"
    )
    assert_cli(result, 0)

    first_metadata_path = (
        pull_dir
        / "releases"
        / first_release_name
        / "annotations"
        / ".v7"
        / "metadata.json"
    )
    assert (
        first_metadata_path.is_file()
    ), f"Expected metadata.json to be present after pull at {first_metadata_path}"

    local_dataset.delete_items(config_values)

    result = run_cli_command(
        f"darwin dataset push {local_dataset.name} {pull_dir}/images --preserve-folders"
    )
    assert_cli(result, 0)
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} {annotation_format} "
        f"{pull_dir}/releases/{first_release_name}/annotations"
    )
    assert_cli(result, 0)

    shutil.rmtree(f"{pull_dir}/images")

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

    second_metadata_path = (
        pull_dir
        / "releases"
        / second_release_name
        / "annotations"
        / ".v7"
        / "metadata.json"
    )

    # Per-annotation and per-item property values must match across the
    # round-trip (unchanged assertion reused from flat-property tests).
    compare_annotations_export(
        Path(f"{pull_dir}/releases/{first_release_name}/annotations"),
        Path(f"{pull_dir}/releases/{second_release_name}/annotations"),
        item_type,
        unzip=False,
    )

    # Nesting-specific assertion: parent/child links and trigger conditions
    # survive the export -> import -> export cycle.
    assert_nested_metadata_round_trips(first_metadata_path, second_metadata_path)
