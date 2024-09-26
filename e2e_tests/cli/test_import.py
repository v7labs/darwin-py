from pathlib import Path

from e2e_tests.helpers import (
    assert_cli,
    run_cli_command,
    export_and_download_annotations,
    delete_annotation_uuids,
)
from e2e_tests.objects import E2EDataset, ConfigValues
from darwin.utils.utils import parse_darwin_json
import tempfile
import zipfile
import darwin.datatypes as dt
from typing import List, Dict


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
):
    """
    Ensures that `expected_annotation.data` is equivalent to `actual_annotation.data`
    """
    assert expected_annotation.data == actual_annotation.data


def assert_same_annotation_properties(
    expected_annotation: dt.Annotation, actual_annotation: dt.Annotation
):
    """
    Ensures that `expected_annotation.properties` is equivalent to `actual_annotation.properties`
    """
    if expected_annotation.properties:
        expected_properties = expected_annotation.properties
        actual_properties = actual_annotation.properties
        assert actual_properties is not None
        for expected_property in expected_properties:
            assert expected_property in actual_properties  # type : ignore


def compare_annotations_export(
    actual_annotations_dir: Path,
    expected_annotations_dir: Path,
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
            assert_same_annotation_data(actual_annotation, expected_annotation)
            assert_same_annotation_properties(expected_annotation, actual_annotation)


def test_import_annotations_without_subtypes_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test importing a set of basic annotations (no sub-types or properties) to a set of
    pre-registered files in a dataset.
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_without_subtypes"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir}"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(actual_annotations_dir, expected_annotations_dir)


def test_import_annotations_with_subtypes_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test importing a set of annotations that includes subtypes & properties to a set of
    pre-registered files in a dataset.
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_with_subtypes"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir}"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(actual_annotations_dir, expected_annotations_dir)


def test_annotation_classes_are_created_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing non-existent annotation classes creates those classes in the
    target Darwin team
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_without_subtypes"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir} --yes"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(actual_annotations_dir, expected_annotations_dir)


def test_annotation_classes_are_created_with_properties_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing non-existent annotation classes with properties creates those
    classes and properties in the target Darwin team
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_new_annotations_with_properties"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir} --yes"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(actual_annotations_dir, expected_annotations_dir)


def test_appending_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that appending annotations to an item with already existing annotations does
    not overwrite the original annotations
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_split_in_two_files"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir} --append"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(actual_annotations_dir, expected_annotations_dir)


def test_overwriting_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that the `--overwrite` flag allows bypassing of the overwrite warning when
    importing to items with already existing annotations
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_without_subtypes"
    )
    # 1st import to create annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir}"
    )
    assert_cli(result, 0)
    # 2nd import to overwrite annotations
    result = run_cli_command(
        f" darwin dataset import {local_dataset.name} darwin {expected_annotations_dir} --overwrite"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        actual_annotations_dir = Path(tmp_dir_str)
        export_and_download_annotations(
            actual_annotations_dir, local_dataset, config_values
        )
        compare_annotations_export(actual_annotations_dir, expected_annotations_dir)


def test_annotation_overwrite_warning(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing annotations to an item with already existing annotations throws
    a warning if not using the `--append` or `--overwrite` flags
    """
    local_dataset.register_read_only_items(config_values)
    expected_annotations_dir = (
        Path(__file__).parents[1]
        / "data"
        / "import"
        / "image_annotations_without_subtypes"
    )
    # 1st import to create annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir}"
    )
    assert_cli(result, 0)
    # 2nd import to trigger overwrite warning
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {expected_annotations_dir}"
    )
    assert "will be overwritten" in result.stdout
