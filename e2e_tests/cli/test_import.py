from pathlib import Path


from e2e_tests.helpers import (
    assert_cli,
    run_cli_command,
    export_and_download_annotations,
    delete_annotation_uuids,
    list_items,
)
from e2e_tests.objects import E2EDataset, ConfigValues
from darwin.utils.utils import parse_darwin_json
import tempfile
import zipfile
import darwin.datatypes as dt
from typing import List, Dict, Optional


def get_actual_annotation_filename(
    expected_filename: str, actual_annotation_files: Dict[str, str]
) -> str:
    """
    For a given expected annotation filename, return the name of the file that
    corresponds to the correct actual annotation file

    These should always be the same unless the test involves appending. In these cases,
    multiple annotation files have been imported (expected files), but only 1 has been
    downloaded (actual files). The expected files cannot be identically named in the
    `expected_annotation_files` dictionary, so this function returns the name of the
    corresponding actual annotation file
    """
    if expected_filename not in actual_annotation_files:
        filename_split = expected_filename.split("-")
        return filename_split[0] + ".json"
    return expected_filename


def find_matching_actual_annotation(
    expected_annotation: dt.Annotation, actual_annotations: List[dt.Annotation]
):
    """
    For a given expected annotation, finds the corresponding actual annotation based on
    the `data` field & the annotation class type
    """
    expected_annotation_data = expected_annotation.data
    expected_annotation_type = expected_annotation.annotation_class.annotation_type
    actual_annotation = next(
        (
            annotation
            for annotation in actual_annotations
            if annotation.data == expected_annotation_data
            and annotation.annotation_class.annotation_type == expected_annotation_type
        ),
        None,
    )
    assert actual_annotation is not None, "Annotation not found in actual annotations"
    return actual_annotation


def assert_same_annotation_data(
    expected_annotation: dt.Annotation, actual_annotation: dt.Annotation
) -> None:
    """
    Ensures that `expected_annotation.data` is equivalent to `actual_annotation.data`
    """
    assert expected_annotation.data == actual_annotation.data


def assert_same_annotation_properties(
    expected_annotation: dt.Annotation, actual_annotation: dt.Annotation
) -> None:
    """
    Ensures that `expected_annotation.properties` is equivalent to `actual_annotation.properties`
    """
    if expected_annotation.properties:
        expected_properties = expected_annotation.properties
        actual_properties = actual_annotation.properties
        assert actual_properties is not None
        for expected_property in expected_properties:
            assert expected_property in actual_properties  # type : ignore


def get_base_slot_name_of_item(
    config_values: ConfigValues, dataset_id: int, item_name: str
) -> str:
    """
    Returns the base slot name for the item with the given name in a specific `E2EDataset`.
    The base slot is always the first listed slot
    """
    items = list_items(
        config_values.api_key,
        dataset_id,
        config_values.team_slug,
        config_values.server,
    )
    for item in items:
        if item["name"] == item_name:
            return item["slots"][0]["slot_name"]


def assert_same_annotation_slot_name(
    expected_annotation: dt.Annotation,
    actual_annotation: dt.Annotation,
    item_type: str,
    base_slot: Optional[str],
) -> None:
    """
    Ensures that the slot tied to an `actual_annotation` is aligned depending on the
    value of `item_type`:
    - `single_slotted`: Perform no checks
    - `multi_slotted`: Ensures `actual_annotation.slot_names` is equivalent to
      `expected_annotation.slot_names`
    - `multi_channel`: Ensures the `actual_annotation` is tied to the base slot
    """
    if item_type == "multi_slotted":
        if expected_annotation.slot_names:
            assert expected_annotation.slot_names == actual_annotation.slot_names
        else:
            assert actual_annotation.slot_names == [base_slot]
    elif item_type == "multi_channel":
        assert actual_annotation.slot_names == [base_slot]


def compare_annotations_export(
    actual_annotations_dir: Path,
    expected_annotations_dir: Path,
    item_type: str,
    base_slot: Optional[str] = "0",
):
    """
    Compares a set of downloaded annotation files with the imported files that resulted
    in those annotations. Ensures equality
    """
    with zipfile.ZipFile(actual_annotations_dir / "dataset.zip") as z:
        z.extractall(actual_annotations_dir)

    file_prefixes_to_ignore = [".", "metadata.json"]
    expected_annotation_files = {
        file.name: str(file)
        for file in expected_annotations_dir.rglob("*")
        if file.is_file()
        and not any(file.name.startswith(prefix) for prefix in file_prefixes_to_ignore)
    }
    actual_annotation_files = {
        file.name: str(file)
        for file in actual_annotations_dir.rglob("*")
        if file.is_file()
        and not any(file.name.startswith(prefix) for prefix in file_prefixes_to_ignore)
    }
    for expected_filename in expected_annotation_files:
        actual_filename = get_actual_annotation_filename(
            expected_filename, actual_annotation_files
        )
        expected_annotations: List[dt.Annotation] = parse_darwin_json(
            Path(expected_annotation_files[expected_filename])
        ).annotations  # type: ignore
        actual_annotations: List[dt.Annotation] = parse_darwin_json(
            Path(actual_annotation_files[actual_filename])
        ).annotations  # type: ignore

        delete_annotation_uuids(expected_annotations)
        delete_annotation_uuids(actual_annotations)

        for expected_annotation in expected_annotations:
            actual_annotation = find_matching_actual_annotation(
                expected_annotation, actual_annotations
            )
            assert_same_annotation_data(expected_annotation, actual_annotation)
            assert_same_annotation_properties(expected_annotation, actual_annotation)
            assert_same_annotation_slot_name(
                expected_annotation, actual_annotation, item_type, base_slot
            )


def run_import_test(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    item_type: str,
    annotations_subdir: str,
    item_name: Optional[str] = None,
    additional_flags: str = "",
    exit_code: int = 0,
    expect_warning: Optional[str] = None,
    expect_error: Optional[str] = None,
) -> None:
    """
    Helper function to run import tests for different item types and annotation configurations.
    """
    local_dataset.register_read_only_items(config_values, item_type)
    expected_annotations_dir = (
        Path(__file__).parents[1] / "data" / "import" / annotations_subdir
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir} {additional_flags}"
    )
    assert_cli(result, exit_code)

    if expect_warning:
        assert expect_warning in result.stdout

    if expect_error:
        assert expect_error in result.stdout
        return

    base_slot = (
        get_base_slot_name_of_item(config_values, local_dataset.id, item_name)
        if item_name
        else None
    )
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(
            actual_annotations_dir, expected_annotations_dir, item_type, base_slot
        )


def test_import_annotations_without_subtypes_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_without_subtypes",
    )


def test_import_annotations_with_subtypes_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_with_subtypes",
    )


def test_annotation_classes_are_created_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_without_subtypes",
        additional_flags="--yes",
    )


def test_annotation_classes_are_created_with_properties_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_new_annotations_with_properties",
        additional_flags="--yes",
    )


def test_appending_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_split_in_two_files",
        additional_flags="--append",
    )


def test_overwriting_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_without_subtypes",
    )
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_without_subtypes",
        additional_flags="--overwrite",
    )


def test_annotation_overwrite_warning(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    # 1st import to create annotations
    local_dataset.register_read_only_items(config_values)
    annotations_subdir = "image_annotations_without_subtypes"
    expected_annotations_dir = (
        Path(__file__).parents[1] / "data" / "import" / annotations_subdir
    )
    run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir}"
    )

    # Run the 2nd import to trigger the overwrite warning
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_without_subtypes",
        expect_warning="will be overwritten",
        exit_code=255,
    )


def test_import_annotations_to_multi_slotted_item_without_slots_defined(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_slotted",
        item_name="multi_slotted_item",
        annotations_subdir="multi_slotted_annotations_without_slots_defined",
    )


def test_import_annotations_to_multi_slotted_item_with_slots_defined(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_slotted",
        item_name="multi_slotted_item",
        annotations_subdir="multi_slotted_annotations_with_slots_defined",
    )


def test_import_annotations_to_multi_channel_item_without_slots_defined(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_channel",
        item_name="multi_channel_item",
        annotations_subdir="multi_channel_annotations_without_slots_defined",
    )


def test_import_annotations_to_multi_channel_item_with_slots_defined(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_channel",
        item_name="multi_channel_item",
        annotations_subdir="multi_channel_annotations_with_slots_defined",
    )


def test_import_annotations_to_multi_channel_item_non_base_slot(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_channel",
        item_name="multi_channel_item",
        annotations_subdir="multi_channel_annotations_aligned_with_non_base_slot",
        expect_error="WARNING: 1 file(s) have the following blocking issues and will not be imported",
    )
