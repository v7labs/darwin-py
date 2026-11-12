import dataclasses
import difflib
import json
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import pytest

import darwin.datatypes as dt
from darwin.importer import get_importer
from e2e_tests.helpers import (
    assert_cli,
    delete_annotation_uuids,
    export_release,
    list_items,
    exclude_annotations_of_type,
    run_cli_command,
    wait_until_items_processed,
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


def sorted_sub_annotations(subs: Sequence[dt.SubAnnotation]) -> List[Dict[str, Any]]:
    """
    Returns the given sub-annotations as plain dictionaries in a stable order, so that
    a comparison ignores the order of the sub-annotations
    """
    return sorted(
        (dataclasses.asdict(sub) for sub in subs),
        key=lambda sub: json.dumps(sub, sort_keys=True, default=str),
    )


def comparable_annotation(
    annotation: Union[dt.Annotation, dt.VideoAnnotation],
) -> Dict[str, Any]:
    """
    Returns the parts of an annotation that must be the same after an import and an export:
    - `dt.Annotation`: the class name, the annotation type, `data` and the sub-annotations
    - `dt.VideoAnnotation`: the class name, the annotation type and each frame, with its
      sub-annotations
    """
    annotation_class = annotation.annotation_class
    if isinstance(annotation, dt.VideoAnnotation):
        frames = {}
        for frame_index, frame in annotation.frames.items():
            frames[frame_index] = dataclasses.asdict(frame)
            frames[frame_index]["subs"] = sorted_sub_annotations(frame.subs)
        return {
            "class_name": annotation_class.name,
            "annotation_type": annotation_class.annotation_type,
            "frames": frames,
        }
    return {
        "class_name": annotation_class.name,
        "annotation_type": annotation_class.annotation_type,
        "data": annotation.data,
        "subs": sorted_sub_annotations(annotation.subs),
    }


def describe_annotation(annotation: Union[dt.Annotation, dt.VideoAnnotation]) -> str:
    annotation_class = annotation.annotation_class
    return f"'{annotation_class.name}' ({annotation_class.annotation_type})"


def closest_annotation_diff(
    expected_annotation: Union[dt.Annotation, dt.VideoAnnotation],
    unmatched_actual_annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
) -> str:
    """
    Returns a diff of the expected annotation and the most similar unmatched actual
    annotation. Actual annotations of the same class are preferred, then of the same type
    """
    if not unmatched_actual_annotations:
        return "There are no unmatched actual annotations to compare with"

    def as_text(annotation: Union[dt.Annotation, dt.VideoAnnotation]) -> str:
        return json.dumps(
            comparable_annotation(annotation), indent=2, sort_keys=True, default=str
        )

    expected_class = expected_annotation.annotation_class
    expected_text = as_text(expected_annotation)

    def similarity(annotation: Union[dt.Annotation, dt.VideoAnnotation]):
        annotation_class = annotation.annotation_class
        same_type = annotation_class.annotation_type == expected_class.annotation_type
        return (
            same_type and annotation_class.name == expected_class.name,
            same_type,
            difflib.SequenceMatcher(
                None, expected_text, as_text(annotation)
            ).quick_ratio(),
        )

    closest = max(unmatched_actual_annotations, key=similarity)
    return "\n".join(
        difflib.unified_diff(
            expected_text.splitlines(),
            as_text(closest).splitlines(),
            fromfile=f"expected {describe_annotation(expected_annotation)}",
            tofile=f"closest actual {describe_annotation(closest)}",
            lineterm="",
        )
    )


def pop_matching_actual_annotation(
    expected_annotation: Union[dt.Annotation, dt.VideoAnnotation],
    unmatched_actual_annotations: List[Union[dt.Annotation, dt.VideoAnnotation]],
) -> Union[dt.Annotation, dt.VideoAnnotation]:
    """
    Removes and returns the actual annotation that has the same class, type,
    `data` / `frames` and sub-annotations as the given expected annotation, so that the actual annotations
    that remain after all expected annotations are matched are extra annotations.

    Fails with a diff of the expected and the closest actual annotation if there is no match
    """
    expected_comparable = comparable_annotation(expected_annotation)
    for index, actual_annotation in enumerate(unmatched_actual_annotations):
        if comparable_annotation(actual_annotation) == expected_comparable:
            return unmatched_actual_annotations.pop(index)
    pytest.fail(
        f"No actual annotation matches the expected annotation "
        f"{describe_annotation(expected_annotation)}:\n"
        + closest_annotation_diff(expected_annotation, unmatched_actual_annotations)
    )


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


def parse_annotation_file(
    annotation_file: str, annotation_format: str
) -> List[dt.AnnotationFile]:
    """
    Parses and returns the annotation file(s) in the file at the given path.
    """
    annotation_data = get_importer(annotation_format)(Path(annotation_file))
    if not isinstance(annotation_data, list):
        annotation_data = [annotation_data]
    return annotation_data


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
    # When annotations are appended, several expected files are imported to 1 item, so
    # they are compared together with the 1 actual file of that item
    expected_by_actual: Dict[str, List[str]] = defaultdict(list)
    for expected_filename in expected_annotation_files:
        actual_filename = get_actual_annotation_filename(
            expected_filename, actual_annotation_files
        )
        expected_by_actual[actual_filename].append(expected_filename)

    for actual_filename, expected_filenames in expected_by_actual.items():
        # A file can hold several items (COCO), so the items are paired by file name
        actual_file_by_item = {
            annotation_file.filename: annotation_file
            for annotation_file in parse_annotation_file(
                actual_annotation_files[actual_filename], annotation_format
            )
        }
        expected_files_by_item: Dict[str, List[dt.AnnotationFile]] = defaultdict(list)
        for expected_filename in expected_filenames:
            for annotation_file in parse_annotation_file(
                expected_annotation_files[expected_filename], annotation_format
            ):
                expected_files_by_item[annotation_file.filename].append(annotation_file)
        unexpected_annotated_items = [
            item_name
            for item_name, annotation_file in actual_file_by_item.items()
            if item_name not in expected_files_by_item and annotation_file.annotations
        ]
        assert not unexpected_annotated_items, (
            f"{actual_filename} has annotations on items that are not expected: "
            + ", ".join(unexpected_annotated_items)
        )
        for (
            item_name,
            expected_annotation_files_of_item,
        ) in expected_files_by_item.items():
            assert (
                item_name in actual_file_by_item
            ), f"{actual_filename} has no item '{item_name}'"
            actual_annotation_file = actual_file_by_item[item_name]
            actual_annotations = actual_annotation_file.annotations
            expected_annotations = [
                annotation
                for expected_annotation_file in expected_annotation_files_of_item
                for annotation in expected_annotation_file.annotations
            ]
            actual_item_level_properties = actual_annotation_file.item_properties or []

            delete_annotation_uuids(expected_annotations)
            delete_annotation_uuids(actual_annotations)

            # We compare mask annotation instances separately: equal sets and counts
            assert_all_expected_mask_instances_present(
                actual_annotations, expected_annotations
            )
            actual_annotations = exclude_annotations_of_type("mask", actual_annotations)
            expected_annotations = exclude_annotations_of_type(
                "mask", expected_annotations
            )

            for expected_annotation_file in expected_annotation_files_of_item:
                assert_same_item_level_properties(
                    expected_annotation_file.item_properties or [],
                    actual_item_level_properties,
                )
            unmatched_actual_annotations = list(actual_annotations)
            for expected_annotation in expected_annotations:
                actual_annotation = pop_matching_actual_annotation(
                    expected_annotation, unmatched_actual_annotations
                )
                assert_same_annotation_properties(
                    expected_annotation, actual_annotation
                )
                assert_same_annotation_slot_name(
                    expected_annotation, actual_annotation, item_type, base_slot
                )
            assert not unmatched_actual_annotations, (
                f"{actual_filename} has {len(unmatched_actual_annotations)} annotation(s) "
                "that are not expected: "
                + ", ".join(
                    describe_annotation(annotation)
                    for annotation in unmatched_actual_annotations
                )
            )


def assert_all_expected_mask_instances_present(
    actual_annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
    expected_annotations: Sequence[Union[dt.Annotation, dt.VideoAnnotation]],
) -> None:
    expected_masks = [
        a for a in expected_annotations if a.annotation_class.annotation_type == "mask"
    ]
    actual_masks = [
        a for a in actual_annotations if a.annotation_class.annotation_type == "mask"
    ]

    def mask_instance(mask: Union[dt.Annotation, dt.VideoAnnotation]) -> str:
        # The class, the sub-annotations and, for videos, the frames, with the slots
        return json.dumps(
            [comparable_annotation(mask), mask.slot_names], sort_keys=True, default=str
        )

    assert Counter(mask_instance(mask) for mask in actual_masks) == Counter(
        mask_instance(mask) for mask in expected_masks
    )
    for expected_mask in expected_masks:
        if expected_mask.properties:
            matching_actual = next(
                (
                    a
                    for a in actual_masks
                    if a.annotation_class.name == expected_mask.annotation_class.name
                    and a.slot_names == expected_mask.slot_names
                ),
                None,
            )
            assert matching_actual is not None
            assert_same_annotation_properties(expected_mask, matching_actual)


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
    # The import rejects items that are still processing. The wait is 1 request for
    # items that are already processed, so it is done for all item types
    wait_until_items_processed(config_values, local_dataset.id, timeout=60)
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


def test_import_eye_annotations_to_videos(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Checks that eye video annotations import and survive a round trip.

    As in the skeleton video fixtures, every frame carries its own payload and
    `only_keyframes` is unset, so keyframe inheritance is not reached here. That
    path is asserted by `test_imports_an_eye_video_annotation`.
    """
    run_import_test(
        local_dataset,
        config_values,
        item_type="single_slotted_video",
        annotations_subdir="video_annotations_with_eye",
    )


def test_import_keypoint_3d_annotations_to_dicom_volumes(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Checks that 3D keypoints keep their voxel position through import and export.
    """
    run_import_test(
        local_dataset,
        config_values,
        item_type="multi_segment_nifti",
        annotations_subdir="keypoint_3d",
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
