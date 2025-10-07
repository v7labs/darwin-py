import shutil
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import orjson as json
import pytest

from darwin.dataset.split_manager import split_dataset
from darwin.dataset.utils import (
    compute_distributions,
    exhaust_generator,
    extract_classes,
    get_annotations,
    get_external_file_type,
    get_release_path,
    parse_external_file_path,
    sanitize_filename,
)
from tests.fixtures import *


def open_resource_file():
    resource_file = (
        Path("tests") / "darwin" / "dataset" / "resources" / "stratified_polygon_train"
    )
    return resource_file.open()


def parsed_annotation_file():
    return {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "test.jpg",
            "path": "/",
            "slots": [
                {
                    "type": "image",
                    "slot_name": "0",
                    "width": 1920,
                    "height": 1080,
                    "source_files": [
                        {
                            "file_name": "test.jpg",
                            "url": "https://darwin.v7labs.com/test.jpg",
                        }
                    ],
                }
            ],
        },
        "annotations": [
            {
                "name": "class_1",
                "polygon": {"paths": [[{"x": 0, "y": 0}]]},
                "slot_names": ["0"],
            },
            {
                "name": "class_1",
                "polygon": {"paths": [[{"x": 0, "y": 0}]]},
                "slot_names": ["0"],
            },
            {
                "name": "class_2",
                "polygon": {"paths": [[{"x": 0, "y": 0}]]},
                "slot_names": ["0"],
            },
            {
                "name": "class_2",
                "polygon": {"paths": [[{"x": 0, "y": 0}]]},
                "slot_names": ["0"],
            },
            {
                "name": "class_2",
                "polygon": {"paths": [[{"x": 0, "y": 0}]]},
                "slot_names": ["0"],
            },
            {
                "name": "class_3",
                "polygon": {"paths": [[{"x": 0, "y": 0}]]},
                "slot_names": ["0"],
            },
        ],
    }


@patch("orjson.loads", return_value=parsed_annotation_file())
@patch("pathlib.Path.open", return_value=open_resource_file())
def test_compute_distributions(parse_file_mock, open_mock):
    value = compute_distributions(Path("test"), Path("split"), partitions=["train"])

    parse_file_mock.assert_called()
    open_mock.assert_called()

    assert value == {
        "class": {"train": {"class_1": 1, "class_2": 1, "class_3": 1}},
        "instance": {"train": {"class_1": 2, "class_2": 3, "class_3": 1}},
    }


class TestExtractClasses:
    @pytest.fixture
    def annotations_path(self, tmp_path: Path):
        # Executed before the test
        annotations_path = tmp_path / "annotations"
        annotations_path.mkdir(parents=True)

        # Useful if the test needs to reuse attrs
        yield annotations_path

        # Executed after the test
        shutil.rmtree(annotations_path)

    def test_builds_correct_mapping_dictionaries(self, annotations_path: Path):
        payload = {
            "version": "2.0",
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
            "item": {
                "name": "0.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "slot_name": "0",
                        "source_files": [
                            {"file_name": "0.jpg", "url": "https://example.com/0.jpg"}
                        ],
                    }
                ],
            },
            "annotations": [
                {"name": "class_1", "polygon": {"paths": [[]]}},
                {
                    "name": "class_2",
                    "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100},
                },
                {"name": "class_3", "polygon": {"paths": [[]]}},
                {"name": "class_4", "tag": {}},
                {"name": "class_1", "polygon": {"paths": [[]]}},
            ],
        }
        _create_annotation_file(annotations_path, "0.json", payload)

        payload = {
            "version": "2.0",
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
            "item": {
                "name": "1.jpg",
                "path": "/",
                "slots": [
                    {
                        "type": "image",
                        "slot_name": "0",
                        "source_files": [
                            {"file_name": "1.jpg", "url": "https://example.com/1.jpg"}
                        ],
                    }
                ],
            },
            "annotations": [
                {"name": "class_5", "polygon": {"paths": [[]]}},
                {
                    "name": "class_6",
                    "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100},
                },
                {"name": "class_1", "polygon": {"paths": [[]]}},
                {"name": "class_4", "tag": {}},
                {"name": "class_1", "polygon": {"paths": [[]]}},
            ],
        }
        _create_annotation_file(annotations_path, "1.json", payload)
        class_dict, index_dict = extract_classes(annotations_path, "polygon")

        assert set(index_dict.keys()) == {0, 1}
        assert index_dict[0] == {"class_1", "class_3"}
        assert index_dict[1] == {"class_1", "class_5"}

        class_dict, index_dict = extract_classes(annotations_path, "bounding_box")

        assert dict(class_dict) == {"class_2": {0}, "class_6": {1}}
        assert dict(index_dict) == {0: {"class_2"}, 1: {"class_6"}}

        class_dict, index_dict = extract_classes(annotations_path, "tag")

        assert dict(class_dict) == {"class_4": {0, 1}}
        assert dict(index_dict) == {0: {"class_4"}, 1: {"class_4"}}

    def test_extract_multiple_annotation_types(self, annotations_path: Path):
        # Provided payloads
        _create_annotation_file(
            annotations_path,
            "0.json",
            {
                "version": "2.0",
                "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
                "item": {
                    "name": "0.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "slot_name": "0",
                            "source_files": [
                                {
                                    "file_name": "0.jpg",
                                    "url": "https://example.com/0.jpg",
                                }
                            ],
                        }
                    ],
                },
                "annotations": [
                    {
                        "name": "class_1",
                        "polygon": {"paths": [[]]},
                        "slot_names": ["0"],
                    },
                    {
                        "name": "class_2",
                        "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100},
                        "slot_names": ["0"],
                    },
                    {
                        "name": "class_3",
                        "polygon": {"paths": [[]]},
                        "slot_names": ["0"],
                    },
                    {"name": "class_4", "slot_names": ["0"]},
                    {
                        "name": "class_1",
                        "polygon": {"paths": [[]]},
                        "slot_names": ["0"],
                    },
                ],
            },
        )
        _create_annotation_file(
            annotations_path,
            "1.json",
            {
                "version": "2.0",
                "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
                "item": {
                    "name": "1.jpg",
                    "path": "/",
                    "slots": [
                        {
                            "type": "image",
                            "slot_name": "0",
                            "source_files": [
                                {
                                    "file_name": "1.jpg",
                                    "url": "https://example.com/1.jpg",
                                }
                            ],
                        }
                    ],
                },
                "annotations": [
                    {
                        "name": "class_5",
                        "polygon": {"paths": [[]]},
                        "slot_names": ["0"],
                    },
                    {
                        "name": "class_6",
                        "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100},
                        "slot_names": ["0"],
                    },
                    {
                        "name": "class_1",
                        "polygon": {"paths": [[]]},
                        "slot_names": ["0"],
                    },
                    {"name": "class_4", "slot_names": ["0"]},
                    {
                        "name": "class_1",
                        "polygon": {"paths": [[]]},
                        "slot_names": ["0"],
                    },
                ],
            },
        )

        # Extracting classes for both bounding_box and polygon annotations
        class_dict, index_dict = extract_classes(
            annotations_path, ["polygon", "bounding_box"]
        )

        # Assertions
        assert set(class_dict.keys()) == {
            "class_1",
            "class_2",
            "class_3",
            "class_5",
            "class_6",
        }
        assert class_dict["class_1"] == {0, 1}
        assert class_dict["class_2"] == {0}
        assert class_dict["class_3"] == {0}
        assert class_dict["class_5"] == {1}
        assert class_dict["class_6"] == {1}

        assert set(index_dict.keys()) == {0, 1}
        assert index_dict[0] == {"class_1", "class_2", "class_3"}
        assert index_dict[1] == {"class_1", "class_5", "class_6"}


class TestSanitizeFilename:
    def test_normal_filenames_stay_untouched(self):
        assert sanitize_filename("test.jpg") == "test.jpg"

    def test_special_characters_are_replaced_with_underscores(self):
        assert (
            sanitize_filename("2020-06-18T08<50<13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename("2020-06-18T08>50>13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename('2020-06-18T08"50"13.14815Z.json')
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename("2020-06-18T08/50/13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename("2020-06-18T08\\50\\13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename("2020-06-18T08|50|13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename("2020-06-18T08?50?13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        assert (
            sanitize_filename("2020-06-18T08*50*13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )

    @patch("platform.system", return_value="Windows")
    def test_replace_columns_on_windows(self, mock: MagicMock):
        assert (
            sanitize_filename("2020-06-18T08:50:13.14815Z.json")
            == "2020-06-18T08_50_13.14815Z.json"
        )
        mock.assert_called_once()

    @patch("platform.system", return_value="Linux")
    def test_avoid_replacing_columns_on_non_windows(self, mock: MagicMock):
        assert (
            sanitize_filename("2020-06-18T08:50:13.14815Z.json")
            == "2020-06-18T08:50:13.14815Z.json"
        )
        mock.assert_called_once()


def _create_annotation_file(annotation_path: Path, filename: str, payload: Dict):
    with open(annotation_path / filename, "w") as f:
        op = json.dumps(payload).decode("utf-8")
        f.write(op)


class TestGetReleasePath:
    def test_defaults_to_latest_version_if_no_version_provided(
        self, team_dataset_path: Path
    ):
        latest_release_path = team_dataset_path / "releases" / "latest"
        latest_release_path.mkdir(parents=True)
        assert get_release_path(team_dataset_path) == latest_release_path

    def test_uses_provided_version_name_otherwise(self, team_dataset_path: Path):
        test_release_path = team_dataset_path / "releases" / "test"
        test_release_path.mkdir(parents=True)
        assert get_release_path(team_dataset_path, "test") == test_release_path


def throw():
    # these need to be top level to be pickle-able
    raise Exception("Test")


def return_1():
    # these need to be top level to be pickle-able
    return 1


class TestExhaustGenerator:
    def test_works_with_no_exceptions(self):
        # test multi-threaded
        successes, errors = exhaust_generator([return_1, return_1], 2, True)
        assert len(errors) == 0
        assert len(successes) == 2
        assert successes == [1, 1]

        # test single-threaded
        successes, errors = exhaust_generator([return_1, return_1], 2, False)
        assert len(errors) == 0
        assert len(successes) == 2
        assert successes == [1, 1]

    def test_passes_back_exceptions(self):
        # test multi-threaded
        successes, errors = exhaust_generator([return_1, throw], 2, True)
        assert len(errors) == 1
        assert len(successes) == 1
        assert isinstance(errors[0], Exception)
        assert errors[0].args[0] == "Test"

        # test single-threaded
        successes, errors = exhaust_generator([return_1, throw], 2, False)
        assert len(errors) == 1
        assert len(successes) == 1
        assert isinstance(errors[0], Exception)
        assert errors[0].args[0] == "Test"


class TestGetExternalFileType:
    def test_get_external_file_types(self):
        assert get_external_file_type("/path/to/file/my_dicom.dcm") == "dicom"
        assert get_external_file_type("/path/to/file/my_pdf.pdf") == "pdf"

        assert get_external_file_type("/path/to/file/my_image.png") == "image"
        assert get_external_file_type("/path/to/file/my_image.jpeg") == "image"
        assert get_external_file_type("/path/to/file/my_image.jpg") == "image"
        assert get_external_file_type("/path/to/file/my_image.jfif") == "image"
        assert get_external_file_type("/path/to/file/my_image.tif") == "image"
        assert get_external_file_type("/path/to/file/my_image.tiff") == "image"
        assert get_external_file_type("/path/to/file/my_image.bmp") == "image"
        assert get_external_file_type("/path/to/file/my_image.svs") == "image"
        assert get_external_file_type("/path/to/file/my_image.webp") == "image"
        assert get_external_file_type("/path/to/file/my_image.JPEG") == "image"
        assert get_external_file_type("/path/to/file/my_image.JPG") == "image"
        assert get_external_file_type("/path/to/file/my_image.BMP") == "image"

        assert get_external_file_type("/path/to/file/my_video.avi") == "video"
        assert get_external_file_type("/path/to/file/my_video.bpm") == "video"
        assert get_external_file_type("/path/to/file/my_video.mov") == "video"
        assert get_external_file_type("/path/to/file/my_video.mp4") == "video"


class TestParseExternalFilePath:
    def test_parse_external_file_paths(self):
        assert parse_external_file_path("my_image.png", preserve_folders=True) == "/"
        assert parse_external_file_path("my_image.png", preserve_folders=False) == "/"

        assert (
            parse_external_file_path("path/to/my_image.png", preserve_folders=True)
            == "/path/to"
        )
        assert (
            parse_external_file_path("path/to/my_image.png", preserve_folders=False)
            == "/"
        )


class TestGetAnnotations:
    def test_basic_functionality(
        self,
    ):
        """
        Basic functionality test for the `get_annotations` function.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = (
                    Path(tmpdir) / "model_training_data" / "classification-test"
                )
                annotations = list(
                    get_annotations(
                        dataset_path=dataset_path,
                        release_name="complete",
                        annotation_type="tag",
                        annotation_format="darwin",
                    )
                )
                assert len(annotations) == 200
                assert annotations[0]["annotations"][0]["tag"] == {}

    def test_partition_handling(
        self,
    ):
        """
        Test the partition handling of the `get_annotations` function.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile("tests/model_training_data.zip") as zfile:
                zfile.extractall(tmpdir)
                dataset_path = (
                    Path(tmpdir) / "model_training_data" / "classification-test"
                )
                split_dataset(
                    dataset_path=dataset_path,
                    release_name="complete",
                    val_percentage=0.1,
                    test_percentage=0.2,
                )
                split_types = ["random", "stratified"]
                partitions = ["test", "train", "val"]
                expected_splits = {
                    "random_test": 40,
                    "random_train": 140,
                    "random_val": 20,
                    "stratified_test": 40,
                    "stratified_train": 140,
                    "stratified_val": 20,
                }
                for split_type in split_types:
                    for partition in partitions:
                        annotations = list(
                            get_annotations(
                                dataset_path=dataset_path,
                                release_name="complete",
                                annotation_type="tag",
                                annotation_format="darwin",
                                partition=partition,
                                split_type=split_type,
                                split="140_20_40",
                            )
                        )
                        assert (
                            len(annotations)
                            == expected_splits[f"{split_type}_{partition}"]
                        )
                        assert annotations[0]["annotations"][0]["tag"] == {}
