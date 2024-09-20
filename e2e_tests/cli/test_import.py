from pathlib import Path

from e2e_tests.helpers import (
    assert_cli,
    run_cli_command,
    normalize_expected_annotation,
    normalize_actual_annotation,
)
from e2e_tests.objects import E2EDataset, ConfigValues
from typing import List, Dict
import json
import pytest


def validate_annotations(
    expected_item_names: List[str],
    annotations: Dict[str, List],
    import_dir: Path,
    properties: Dict[str, List],
    number_of_annotations: int,
):
    """
    Compare the state of imported annotations against the files that were imported
    """
    for item in expected_item_names:
        item_annotations = annotations[item]
        assert len(item_annotations) == number_of_annotations
        with open(import_dir / Path(f"{item}.json"), "r") as file:
            expected_item_annotations = json.load(file)["annotations"]

        # Normalize annotations for comparison
        normalized_expected_annotations = [
            normalize_expected_annotation(annotation)
            for annotation in expected_item_annotations
        ]
        normalized_actual_annotations = [
            normalize_actual_annotation(annotation, properties) for annotation in item_annotations  # type: ignore
        ]

        # Check if every expected annotation is in the actual annotations
        for expected_annotation in normalized_expected_annotations:
            assert (
                expected_annotation in normalized_actual_annotations
            ), f"Expected annotation {expected_annotation} not found in actual annotations"


def validate_annotation_classes(
    annotation_classes: Dict[str, List], expected_annotation_class_names: List[str]
):
    """
    Compares the state of a team's annotation classes against an expected set of annotation class names
    """
    annotation_class_names = [
        annotation_class["name"]
        for annotation_class in annotation_classes["annotation_classes"]
    ]
    for expected_class_name in expected_annotation_class_names:
        assert (
            expected_class_name in annotation_class_names
        ), f"Expected annotation class name {expected_class_name} not found in actual annotation class names"


def test_import_basic_annotations_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test importing a set of basic annotations (no sub-types or properties) to a set of pre-registered files in a dataset.
    """
    expected_item_names = [
        "image_1",
        "image_2",
        "image_3",
        "image_4",
        "image_4",
        "image_5",
        "image_6",
        "image_7",
        "image_8",
    ]
    number_of_annotations = 9  # One annotation of each type
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_basic_annotations"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert_cli(result, 0)
    annotations, annotation_classes, properties = local_dataset.get_annotation_data(
        config_values
    )
    validate_annotations(
        expected_item_names, annotations, import_dir, properties, number_of_annotations
    )


def test_import_annotations_with_subtypes_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test importing a set of basic annotations includes subtypes & properties to a set of pre-registered files in a dataset.
    """
    expected_item_names = [
        "image_1",
        "image_2",
        "image_3",
        "image_4",
        "image_4",
        "image_5",
        "image_6",
        "image_7",
        "image_8",
    ]
    number_of_annotations = 9  # One annotation of each type
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_with_subtypes"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert_cli(result, 0)
    annotations, _, properties = local_dataset.get_annotation_data(config_values)
    validate_annotations(
        expected_item_names, annotations, import_dir, properties, number_of_annotations
    )


# TODO, implement video annotation import tests:
# test_import_basic_annotations_to_videos
# test_import_annotations_with_subtypes_to_videos


def test_annotation_classes_are_created_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing non-existent annotation classes creates those classes in the target Darwin team
    """
    expected_item_names = [
        "image_1",
        "image_2",
        "image_3",
        "image_4",
        "image_4",
        "image_5",
        "image_6",
        "image_7",
        "image_8",
    ]
    expected_annotation_class_names = [
        "new_test_bounding_box_basic",
        "new_test_ellipse_basic",
        "new_test_keypoint_basic",
        "new_test_line_basic",
        "new_test_mask_basic",
        "new_test_polygon_basic",
        "new_test_tag_basic",
    ]
    number_of_annotations = 8  # One annotation of each type except skeletons, since these cannot be created during import
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_new_basic_annotations"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir} --yes"
    )
    assert_cli(result, 0)
    annotations, annotation_classes, properties = local_dataset.get_annotation_data(
        config_values
    )
    validate_annotations(
        expected_item_names, annotations, import_dir, properties, number_of_annotations
    )
    validate_annotation_classes(annotation_classes, expected_annotation_class_names)


@pytest.mark.skip(reason="Skipping this test while DAR-3920 is being worked on")
def test_annotation_classes_are_created_with_properties_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing non-existent annotation classes with properties creates those classes and properties in the target Darwin team
    """
    expected_item_names = [
        "image_1",
        "image_2",
        "image_3",
        "image_4",
        "image_4",
        "image_5",
        "image_6",
        "image_7",
        "image_8",
    ]
    expected_annotation_class_names = [
        "new_test_bounding_box_with_properties",
        "new_test_ellipse_with_properties",
        "new_test_keypoint_with_properties",
        "new_test_line_with_properties",
        "new_test_mask_with_properties",
        "new_test_polygon_with_properties",
        "new_test_tag_with_properties",
    ]
    number_of_annotations = 8  # One annotation of each type except skeletons, since these cannot be created during import
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_new_annotations_with_properties"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir} --yes"
    )
    assert_cli(result, 0)
    annotations, annotation_classes, properties = local_dataset.get_annotation_data(
        config_values
    )
    validate_annotations(
        expected_item_names, annotations, import_dir, properties, number_of_annotations
    )
    validate_annotation_classes(annotation_classes, expected_annotation_class_names)


def test_appending_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that appending annotations to an item with already existing annotations does not overwrite the original annotations
    """
    expected_item_names = [
        "image_1",
        "image_2",
        "image_3",
        "image_4",
        "image_4",
        "image_5",
        "image_6",
        "image_7",
        "image_8",
    ]
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_basic_annotations"
    )
    # 1st import to create annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert_cli(result, 0)
    # 2nd import to append more annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir} --append"
    )
    assert_cli(result, 0)
    annotations, _, _ = local_dataset.get_annotation_data(config_values)
    for expected_item_name in expected_item_names:
        item_annotations = annotations[expected_item_name]
        assert (
            len(item_annotations) == 15
        )  # 15 because tag, raster_layer, and mask are not added again during the 2nd import


def test_overwriting_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that the `--overwrite` flag allows bypassing of the overwrite warning when importing to items with already existing annotations
    """
    expected_item_names = [
        "image_1",
        "image_2",
        "image_3",
        "image_4",
        "image_4",
        "image_5",
        "image_6",
        "image_7",
        "image_8",
    ]
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_basic_annotations"
    )
    # 1st import to create annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert_cli(result, 0)
    # 2nd import to overwrite annotations
    result = run_cli_command(
        f" darwin dataset import {local_dataset.name} darwin {import_dir} --overwrite"
    )
    assert_cli(result, 0)
    annotations, _, _ = local_dataset.get_annotation_data(config_values)
    for expected_item_name in expected_item_names:
        item_annotations = annotations[expected_item_name]
        assert len(item_annotations) == 9


def test_annotation_overwrite_warning(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing annotations to an item with already existing annotations throws a warning if not using the `--append` or `--overwrite` flags
    """
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_basic_annotations"
    )
    # 1st import to create annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert_cli(result, 0)
    # 2nd import to trigger overwrite warning
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert "will be overwritten" in result.stdout


# TODO
# def test_importing_coco_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     assert 1 == 2
#     """
#     Test that the coco annotation importer is working
#     """


# TODO
# def test_importing_csv_tags_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     assert 1 == 2
#     """
#     Test that the csv_tags annotation importer is working
#     """


# TODO:
# def test_importing_csv_tags_video_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     assert 1 == 2
#     """
#     Test that the csv_tags_video annotation importer is working
#     """


# TODO:
# def test_importing_dataloop_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     """
#     Test that the dataloop annotation importer is working
#     """


# TODO:
# def test_importing_labelbox_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     """
#     Test that the labelbox annotation importer is working
#     """

# TODO
# This one is a bit more involved: We can only import NifTI annotations to certain filetypes, so how should we deal with this?
# def test_importing_nifti_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     """
#     Test that the nifti annotation importer is working
#     """


# TODO
# def test_importing_pascal_voc_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     """
#     Test that the pascal_voc annotation importer is working
#     """


# TODO
# def test_importing_superannotate_annotations(
#     local_dataset: E2EDataset, config_values: ConfigValues
# ) -> None:
#     """
#     Test that the superannotate annotation importer is working
#     """
