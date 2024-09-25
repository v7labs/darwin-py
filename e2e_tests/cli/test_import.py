from pathlib import Path

from e2e_tests.helpers import (
    assert_cli,
    run_cli_command,
    export_and_download_annotations,
)
from e2e_tests.objects import E2EDataset, ConfigValues
from darwin.utils.utils import parse_darwin_json
import tempfile
import zipfile


def validate_downloaded_annotations(
    tmp_dir: Path, import_dir: Path, appending: bool = False
):
    """
    Validate that the annotations downloaded from a release match the annotations in
    a particular directory, ignoring hidden files.

    If `appending` is set, then the number of actual annotations should exceed the
    number of expected annotations
    """
    annotations_dir = tmp_dir / "annotations"
    with zipfile.ZipFile(tmp_dir / "dataset.zip") as z:
        z.extractall(annotations_dir)
        expected_annotation_files = {
            file.name: str(file)
            for file in import_dir.iterdir()
            if file.is_file() and not file.name.startswith(".")
        }
        actual_annotation_files = {
            file.name: str(file)
            for file in annotations_dir.iterdir()
            if file.is_file() and not file.name.startswith(".")
        }
        for file in expected_annotation_files:
            assert file in actual_annotation_files
            expected_annotations = parse_darwin_json(
                Path(expected_annotation_files[file])
            ).annotations  # type: ignore
            actual_annotations = parse_darwin_json(
                Path(actual_annotation_files[file])
            ).annotations  # type: ignore

            # Delete generated UUIDs as these will break asserting equality
            for annotation in expected_annotations:
                del [annotation.id]  # type: ignore
                if annotation.annotation_class.annotation_type == "raster_layer":
                    del [annotation.data["mask_annotation_ids_mapping"]]  # type: ignore
            for annotation in actual_annotations:
                del [annotation.id]  # type: ignore
                if annotation.annotation_class.annotation_type == "raster_layer":
                    del [annotation.data["mask_annotation_ids_mapping"]]  # type: ignore

            # Check that every expected annotation was imported
            if appending:
                assert len(actual_annotations) > len(expected_annotations)
            else:
                assert len(expected_annotations) == len(actual_annotations)
            for annotation in expected_annotations:
                assert annotation in actual_annotations


def test_import_basic_annotations_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test importing a set of basic annotations (no sub-types or properties) to a set of pre-registered files in a dataset.
    """
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_basic_annotations"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir}"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        export_and_download_annotations(tmp_dir, local_dataset, config_values)
        validate_downloaded_annotations(tmp_dir, import_dir)


def test_import_annotations_with_subtypes_to_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test importing a set of basic annotations includes subtypes & properties to a set of pre-registered files in a dataset.
    """
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
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        export_and_download_annotations(tmp_dir, local_dataset, config_values)
        validate_downloaded_annotations(tmp_dir, import_dir)


# TODO, implement video annotation import tests:
# test_import_basic_annotations_to_videos
# test_import_annotations_with_subtypes_to_videos


def test_annotation_classes_are_created_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing non-existent annotation classes creates those classes in the target Darwin team
    """
    local_dataset.register_read_only_items(config_values)
    import_dir = (
        Path(__file__).parents[1] / "data" / "import" / "image_new_basic_annotations"
    )
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir} --yes"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        export_and_download_annotations(tmp_dir, local_dataset, config_values)
        validate_downloaded_annotations(tmp_dir, import_dir)


def test_annotation_classes_are_created_with_properties_on_import(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that importing non-existent annotation classes with properties creates those classes and properties in the target Darwin team
    """
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
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        export_and_download_annotations(tmp_dir, local_dataset, config_values)
        validate_downloaded_annotations(tmp_dir, import_dir)


def test_appending_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that appending annotations to an item with already existing annotations does not overwrite the original annotations
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
    # 2nd import to append more annotations
    result = run_cli_command(
        f"darwin dataset import {local_dataset.name} darwin {import_dir} --append"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        export_and_download_annotations(tmp_dir, local_dataset, config_values)
        validate_downloaded_annotations(tmp_dir, import_dir, appending=True)


def test_overwriting_annotations(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that the `--overwrite` flag allows bypassing of the overwrite warning when importing to items with already existing annotations
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
    # 2nd import to overwrite annotations
    result = run_cli_command(
        f" darwin dataset import {local_dataset.name} darwin {import_dir} --overwrite"
    )
    assert_cli(result, 0)
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        export_and_download_annotations(tmp_dir, local_dataset, config_values)
        validate_downloaded_annotations(tmp_dir, import_dir)


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
