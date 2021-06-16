from pathlib import Path

from unittest.mock import patch

import darwin.datatypes as dt
from darwin.dataset.utils import compute_distributions


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


@patch("json.load", return_value=parsed_annotation_file())
@patch("pathlib.Path.open", return_value=open_resource_file())
def test_compute_distributions(parse_file_mock, open_mock):
    value = compute_distributions(Path("test"), Path("split"), partitions=["train"])

    parse_file_mock.assert_called()
    open_mock.assert_called()

    assert value == {
        "class": {"train": {"class_1": 1, "class_2": 1, "class_3": 1}},
        "instance": {"train": {"class_1": 2, "class_2": 3, "class_3": 1}},
    }

