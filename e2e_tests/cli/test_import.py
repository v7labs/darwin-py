from collections import defaultdict
import importlib
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import darwin.datatypes as dt
from e2e_tests.helpers import (
    assert_cli,
    delete_annotation_uuids,
    export_release,
    list_items,
    run_cli_command,
)
from e2e_tests.objects import ConfigValues, E2EDataset


def compare_local_annotations_with_uploaded_annotations(
    annotation_format: str,
    local_dataset: E2EDataset,
    config_values: ConfigValues,
) -> None:
    """
    Checks that every annotation uploaded to every item of the given `local_dataset` is
    of the expected type given the annotation format

    This is necessary to verify that imports of formats that cannot be exported are successful
    """
    expected_annotation_types = {
        "csv_tags": "tag",
        "csv_tags_video": "tag",
    }
    video_formats = ["csv_tags_video"]
    expected_annotation_type = expected_annotation_types[annotation_format]
    all_item_annotations, _, _ = local_dataset.get_annotation_data(config_values)
    for item in local_dataset.items:
        item_name = item.name
        item_annotations = all_item_annotations[item_name]
        for item_annotation in item_annotations:
            if annotation_format in video_formats:
                frame_indices = item_annotation["data"]["frames"].keys()
                for frame_index in frame_indices:
                    assert (
                        expected_annotation_type
                        in item_annotation["data"]["frames"][frame_index]
                    )
            else:
                assert expected_annotation_type in item_annotation["data"]


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
    expected_annotation: Union[dt.Annotation, dt.VideoAnnotation],
    actual_annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
) -> Union[dt.Annotation, dt.VideoAnnotation]:
    """
    For a given expected annotation, finds the corresponding actual annotation
    """
    if isinstance(expected_annotation, dt.Annotation):
        expected_annotation_data = expected_annotation.data
        expected_annotation_type = expected_annotation.annotation_class.annotation_type
        actual_annotation = next(
            (
                annotation
                for annotation in actual_annotations
                if annotation.data == expected_annotation_data
                and annotation.annotation_class.annotation_type
                == expected_annotation_type
            ),
            None,
        )
    elif isinstance(expected_annotation, dt.VideoAnnotation):
        expected_annotation_frame_data = expected_annotation.frames
        expected_annotation_type = expected_annotation.annotation_class.annotation_type
        actual_annotation = next(
            (
                annotation
                for annotation in actual_annotations
                if annotation.frames == expected_annotation_frame_data
                and annotation.annotation_class.annotation_type
                == expected_annotation_type
            )
        )
    assert actual_annotation is not None, "Annotation not found in actual annotations"
    return actual_annotation


def assert_same_annotation_data(
    expected_annotation: Union[dt.Annotation, dt.VideoAnnotation],
    actual_annotation: Union[dt.Annotation, dt.VideoAnnotation],
) -> None:
    """
    For `dt.Annotation` objects:
        Ensures that `expected_annotation.data` is equivalent to `actual_annotation.data`

    For `dt.VideoAnnotation` objects:
        Ensures that `expected_annotation.frames` is equivalent to `actual_annotation.frames`
    """
    if isinstance(expected_annotation, dt.Annotation) and isinstance(
        actual_annotation, dt.Annotation
    ):
        assert expected_annotation.data == actual_annotation.data
    elif isinstance(expected_annotation, dt.VideoAnnotation) and isinstance(
        actual_annotation, dt.VideoAnnotation
    ):
        assert expected_annotation.frames == actual_annotation.frames


def assert_same_annotation_properties(
    expected_annotation: Union[dt.Annotation, dt.VideoAnnotation],
    actual_annotation: Union[dt.Annotation, dt.VideoAnnotation],
) -> None:
    """
    Ensures that `expected_annotation.properties` is equivalent to `actual_annotation.properties`
    """
    if expected_annotation.properties:
        expected_properties = expected_annotation.properties
        actual_properties = actual_annotation.properties
        assert actual_properties is not None
        for expected_property in expected_properties:
            assert expected_property in actual_properties


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


def parse_expected_and_actual_annotations(
    expected_annotation_files,
    actual_annotation_files,
    expected_filename: str = "",
    actual_filename: str = "",
    annotation_format: str = "",
) -> Tuple[List[dt.AnnotationFile], List[dt.AnnotationFile]]:
    """
    Parses and returns exported & actual annotation files in a given format.
    """
    importer_module = importlib.import_module(
        f"darwin.importer.formats.{annotation_format}"
    )
    expected_annotation_data = importer_module.parse_path(
        Path(expected_annotation_files[expected_filename])
    )
    actual_annotation_data = importer_module.parse_path(
        Path(actual_annotation_files[actual_filename])
    )

    if not isinstance(expected_annotation_data, list):
        expected_annotation_data = [expected_annotation_data]
    if not isinstance(actual_annotation_data, list):
        actual_annotation_data = [actual_annotation_data]

    return expected_annotation_data, actual_annotation_data


def assert_same_annotation_slot_name(
    expected_annotation: Union[dt.Annotation, dt.VideoAnnotation],
    actual_annotation: Union[dt.Annotation, dt.VideoAnnotation],
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


def assert_same_item_level_properties(
    expected_item_level_properties: List[Dict[str, Any]],
    actual_item_level_properties: List[Dict[str, Any]],
) -> None:
    """
    Ensures that all expected item-level properties are present in exported item-level properties
    """
    for expected_item_level_property in expected_item_level_properties:
        if expected_item_level_property["value"] is not None:
            assert expected_item_level_property in actual_item_level_properties


def compare_annotations_export(
    actual_annotations_dir: Path,
    expected_annotations_dir: Path,
    item_type: str,
    base_slot: Optional[str] = "0",
    annotation_format: str = "darwin",
    unzip: Optional[bool] = True,
):
    """
    Compares a set of downloaded annotation files with the imported files that resulted
    in those annotations. Ensures equality
    """
    if unzip:
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
        (
            expected_annotation_data,
            actual_annotation_data,
        ) = parse_expected_and_actual_annotations(
            expected_annotation_files,
            actual_annotation_files,
            expected_filename,
            actual_filename,
            annotation_format,
        )
        for idx, expected_annotation_file in enumerate(expected_annotation_data):
            actual_annotation_file = actual_annotation_data[idx]
            expected_annotations = expected_annotation_file.annotations
            actual_annotations = actual_annotation_file.annotations
            expected_item_level_properties = (
                expected_annotation_file.item_properties or []
            )
            actual_item_level_properties = actual_annotation_file.item_properties or []

            delete_annotation_uuids(expected_annotations)
            delete_annotation_uuids(actual_annotations)

            # Because we support mask instances, multiple mask annotations with
            # the same annotation class id can be in the same slot.
            (
                non_mask_actual_annotations,
                non_mask_expected_annotations,
            ) = compare_and_omit_mask_annotations(
                actual_annotations,
                expected_annotations
            )

            assert_same_item_level_properties(
                expected_item_level_properties, actual_item_level_properties
            )
            for expected_annotation in non_mask_expected_annotations:
                actual_annotation = find_matching_actual_annotation(
                    expected_annotation, non_mask_actual_annotations
                )
                assert_same_annotation_data(expected_annotation, actual_annotation)
                assert_same_annotation_properties(
                    expected_annotation, actual_annotation
                )
                assert_same_annotation_slot_name(
                    expected_annotation, actual_annotation, item_type, base_slot
                )


def compare_and_omit_mask_annotations(
    actual_annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
    expected_annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
):
    non_mask_actual_annotations = []
    non_mask_expected_annotations = []
    mask_instances_to_match = []

    for expected_annotation in expected_annotations:
        if expected_annotation.annotation_class.annotation_type != "mask":
            non_mask_expected_annotations.append(expected_annotation)
            continue

        mask_instances_to_match.append(
            (
                expected_annotation.annotation_class.name,
                *expected_annotation.slot_names,
            )
        )

    for actual_annotation in actual_annotations:
        if actual_annotation.annotation_class.annotation_type != "mask":
            non_mask_actual_annotations.append(actual_annotation)
            continue

        mask_instances_to_match.remove(
            (
                actual_annotation.annotation_class.name,
                *actual_annotation.slot_names,
            )
        )

    assert not mask_instances_to_match
    return non_mask_actual_annotations, non_mask_expected_annotations


def run_import_test(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    item_type: str,
    annotations_subdir: str,
    annotation_format: Optional[str] = "darwin",
    files_in_flat_structure: bool = False,
    export_only: Optional[bool] = False,
    item_name: Optional[str] = None,
    additional_flags: str = "",
    exit_code: int = 0,
    expect_warning: Optional[str] = None,
    expect_error: Optional[str] = None,
) -> None:
    """
    Helper function to run import tests for different item types and annotation configurations.
    """
    local_dataset.register_read_only_items(
        config_values, item_type, files_in_flat_structure
    )
    expected_annotations_dir = (
        Path(__file__).parents[1] / "data" / "import" / annotations_subdir
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} {annotation_format} {expected_annotations_dir} {additional_flags}"
    )
    assert_cli(result, exit_code)

    if expect_warning:
        assert expect_warning in result.stdout

    if expect_error:
        assert expect_error in result.stdout
        return

    if export_only:
        compare_local_annotations_with_uploaded_annotations(
            annotation_format, local_dataset, config_values  # type: ignore
        )
        return

    base_slot = (
        get_base_slot_name_of_item(config_values, local_dataset.id, item_name)
        if item_name
        else None
    )
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        release = export_release(
            annotation_format,  # type: ignore
            local_dataset,
            config_values,
        )
        release.download_zip(actual_annotations_dir / "dataset.zip")
        compare_annotations_export(
            actual_annotations_dir,
            expected_annotations_dir,
            item_type,
            base_slot,
            annotation_format,  # type: ignore
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


def test_import_existing_item_level_properties(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_with_item_level_properties",
    )


def test_item_level_properties_can_be_imported_without_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_annotations_item_level_properties_no_annotations",
    )


def test_item_level_property_classes_are_created_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="image_new_annotations_with_item_level_properties",
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


def test_import_annotations_to_multi_slotted_item_with_dicom_slots(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_slotted_dicom",
        annotations_subdir="multi_slotted_annotations_with_dicom_slots",
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


def test_import_basic_annotations_to_videos(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted_video",
        annotations_subdir="video_annotations_without_subtypes",
    )


def test_import_annotations_with_subtypes_to_videos(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted_video",
        annotations_subdir="video_annotations_with_subtypes",
    )


def test_importing_coco_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    annotation_format = "coco"
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="coco_annotations",
        annotation_format=annotation_format,
        files_in_flat_structure=True,
    )


def test_importing_csv_tags_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    annotation_format = "csv_tags"
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="csv_tag_annotations",
        annotation_format=annotation_format,
        export_only=True,
    )


def test_importing_csv_tags_video_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    annotation_format = "csv_tags_video"
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted_video",
        annotations_subdir="csv_tag_video_annotations",
        annotation_format=annotation_format,
        export_only=True,
    )


def test_importing_pascal_voc_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    annotation_format = "pascal_voc"
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted",
        annotations_subdir="pascal_voc_annotations",
        annotation_format=annotation_format,
    )
