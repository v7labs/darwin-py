import shutil
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import orjson as json
import pytest

from darwin.dataset.utils import (
    compute_distributions,
    exhaust_generator,
    extract_classes,
    get_release_path,
    sanitize_filename,
)
from tests.fixtures import *


def open_resource_file():
    resource_file = Path("tests") / "darwin" / "dataset" / "resources" / "stratified_polygon_train"
    return resource_file.open()


def parsed_annotation_file():
    return {
        "annotations": [
            {"name": "class_1", "polygon": {"path": []}},
            {"name": "class_1", "polygon": {"path": []}},
            {"name": "class_2", "polygon": {"path": []}},
            {"name": "class_2", "polygon": {"path": []}},
            {"name": "class_2", "polygon": {"path": []}},
            {"name": "class_3", "polygon": {"path": []}},
        ],
        "image": {"filename": "test.jpg", "height": 1080, "url": "https://darwin.v7labs.com/test.jpg", "width": 1920},
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
            "annotations": [
                {"name": "class_1", "polygon": {"path": []}},
                {"name": "class_2", "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100}},
                {"name": "class_3", "polygon": {"path": []}},
                {"name": "class_4", "tag": {}},
                {"name": "class_1", "polygon": {"path": []}},
            ],
            "image": {"filename": "0.jpg"},
        }
        _create_annotation_file(annotations_path, "0.json", payload)

        payload = {
            "annotations": [
                {"name": "class_5", "polygon": {"path": []}},
                {"name": "class_6", "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100}},
                {"name": "class_1", "polygon": {"path": []}},
                {"name": "class_4", "tag": {}},
                {"name": "class_1", "polygon": {"path": []}},
            ],
            "image": {"filename": "1.jpg"},
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
                "annotations": [
                    {"name": "class_1", "polygon": {"path": []}},
                    {"name": "class_2", "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100}},
                    {"name": "class_3", "polygon": {"path": []}},
                    {"name": "class_4", "tag": {}},
                    {"name": "class_1", "polygon": {"path": []}},
                ],
                "image": {"filename": "0.jpg"},
            },
        )
        _create_annotation_file(
            annotations_path,
            "1.json",
            {
                "annotations": [
                    {"name": "class_5", "polygon": {"path": []}},
                    {"name": "class_6", "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100}},
                    {"name": "class_1", "polygon": {"path": []}},
                    {"name": "class_4", "tag": {}},
                    {"name": "class_1", "polygon": {"path": []}},
                ],
                "image": {"filename": "1.jpg"},
            },
        )

        # Extracting classes for both bounding_box and polygon annotations
        class_dict, index_dict = extract_classes(annotations_path, ["polygon", "bounding_box"])

        # Assertions
        assert set(class_dict.keys()) == {"class_1", "class_2", "class_3", "class_5", "class_6"}
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
        assert sanitize_filename("2020-06-18T08<50<13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08>50>13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename('2020-06-18T08"50"13.14815Z.json') == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08/50/13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08\\50\\13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08|50|13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08?50?13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08*50*13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"

    @patch("platform.system", return_value="Windows")
    def test_replace_columns_on_windows(self, mock: MagicMock):
        assert sanitize_filename("2020-06-18T08:50:13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        mock.assert_called_once()

    @patch("platform.system", return_value="Linux")
    def test_avoid_replacing_columns_on_non_windows(self, mock: MagicMock):
        assert sanitize_filename("2020-06-18T08:50:13.14815Z.json") == "2020-06-18T08:50:13.14815Z.json"
        mock.assert_called_once()


def _create_annotation_file(annotation_path: Path, filename: str, payload: Dict):
    with open(annotation_path / filename, "w") as f:
        op = json.dumps(payload).decode("utf-8")
        f.write(op)


class TestGetReleasePath:
    def test_defaults_to_latest_version_if_no_version_provided(self, team_dataset_path: Path):
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


'''
class TestGetAnnotations:
    def test_basic_functionality(
        self,
        team_extracted_dataset_path,
        team_dataset_release_path,
        annotations_path,
        split_path
    ):
        """
        Basic functionality test for the `get_annotations` function.
        """
        
        # Test with basic setup
        annotations = list(get_annotations(dataset_path=team_extracted_dataset_path))
        assert len(annotations) > 0, "Expected to find some annotations"

        # Add more assertions here to validate the structure of the returned annotations

    def test_partition_handling(
        self,
        team_extracted_dataset_path,
        team_dataset_release_path,
        annotations_path,
        split_path
    ):
        """
        Test the partition handling of the `get_annotations` function.
        """

        # Assuming there's a train partition in the test dataset
        annotations = list(get_annotations(dataset_path=team_extracted_dataset_path, partition="train"))
        assert len(annotations) > 0, "Expected to find some annotations for the train partition"

        # Add more assertions here to validate the structure of the returned annotations
        # Repeat for other partitions (e.g., val, test) if present in the mock data
'''
