import json
import shutil
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import pytest

from darwin.dataset.utils import (
    compute_distributions,
    extract_classes,
    get_release_path,
    sanitize_filename,
)

# from tests.fixtures import


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
        "image": {
            "filename": "test.jpg",
            "height": 1080,
            "url": "https://darwin.v7labs.com/test.jpg",
            "width": 1920,
        },
    }


@patch("darwin.json.load", return_value=parsed_annotation_file())
@patch("pathlib.Path.open", return_value=open_resource_file())
def test_compute_distributions(parse_file_mock, open_mock):
    value = compute_distributions(Path("test"), Path("split"), partitions=["train"])

    parse_file_mock.assert_called()
    open_mock.assert_called()

    assert value == {
        "class": {"train": {"class_1": 1, "class_2": 1, "class_3": 1}},
        "instance": {"train": {"class_1": 2, "class_2": 3, "class_3": 1}},
    }


def describe_extract_classes():
    @pytest.fixture
    def annotations_path(tmp_path: Path):
        # Executed before the test
        annotations_path = tmp_path / "annotations"
        annotations_path.mkdir(parents=True)

        # Useful if the test needs to reuse attrs
        yield annotations_path

        # Executed after the test
        shutil.rmtree(annotations_path)

    def builds_correct_mapping_dictionaries(annotations_path: Path):
        payload = {
            "annotations": [
                {"name": "class_1", "polygon": {"path": []}},
                {
                    "name": "class_2",
                    "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100},
                },
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
                {
                    "name": "class_6",
                    "bounding_box": {"x": 0, "y": 0, "w": 100, "h": 100},
                },
                {"name": "class_1", "polygon": {"path": []}},
                {"name": "class_4", "tag": {}},
                {"name": "class_1", "polygon": {"path": []}},
            ],
            "image": {"filename": "1.jpg"},
        }
        _create_annotation_file(annotations_path, "1.json", payload)

        class_dict, index_dict = extract_classes(annotations_path, "polygon")

        assert dict(class_dict) == {"class_1": {0, 1}, "class_3": {0}, "class_5": {1}}
        assert dict(index_dict) == {
            0: {"class_1", "class_3"},
            1: {"class_1", "class_5"},
        }

        class_dict, index_dict = extract_classes(annotations_path, "bounding_box")

        assert dict(class_dict) == {"class_2": {0}, "class_6": {1}}
        assert dict(index_dict) == {0: {"class_2"}, 1: {"class_6"}}

        class_dict, index_dict = extract_classes(annotations_path, "tag")

        assert dict(class_dict) == {"class_4": {0, 1}}
        assert dict(index_dict) == {0: {"class_4"}, 1: {"class_4"}}


def describe_sanitize_filename():
    def normal_filenames_stay_untouched():
        assert sanitize_filename("test.jpg") == "test.jpg"

    def special_characters_are_replaced_with_underscores():
        assert sanitize_filename("2020-06-18T08<50<13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08>50>13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename('2020-06-18T08"50"13.14815Z.json') == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08/50/13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08\\50\\13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08|50|13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08?50?13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        assert sanitize_filename("2020-06-18T08*50*13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"

    @patch("platform.system", return_value="Windows")
    def replace_columns_on_windows(mock: MagicMock):
        assert sanitize_filename("2020-06-18T08:50:13.14815Z.json") == "2020-06-18T08_50_13.14815Z.json"
        mock.assert_called_once()

    @patch("platform.system", return_value="Linux")
    def avoid_replacing_columns_on_non_windows(mock: MagicMock):
        assert sanitize_filename("2020-06-18T08:50:13.14815Z.json") == "2020-06-18T08:50:13.14815Z.json"
        mock.assert_called_once()


def _create_annotation_file(annotation_path: Path, filename: str, payload: Dict):
    with open(annotation_path / filename, "w") as f:
        json.dump(payload, f)


def describe_get_release_path():
    def it_defaults_to_latest_version_if_no_version_provided(team_dataset_path: Path):
        latest_release_path = team_dataset_path / "releases" / "latest"
        latest_release_path.mkdir(parents=True)
        assert get_release_path(team_dataset_path) == latest_release_path

    def it_uses_provided_version_name_otherwise(team_dataset_path: Path):
        test_release_path = team_dataset_path / "releases" / "test"
        test_release_path.mkdir(parents=True)
        assert get_release_path(team_dataset_path, "test") == test_release_path
