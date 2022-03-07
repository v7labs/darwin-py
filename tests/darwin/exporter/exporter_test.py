import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from darwin.datatypes import ExportParser
from darwin.exporter import export_annotations, get_exporter


def describe_export_annotations_for_yolo():
    @pytest.fixture
    def parser():
        parser: ExportParser = get_exporter("yolo")
        return parser

    @pytest.fixture
    def folder_path(tmp_path: Path):
        path: Path = tmp_path / "export_folder"
        yield path
        shutil.rmtree(path)

    @pytest.fixture
    def annotation_file_1(tmp_path: Path):
        filename = "bbox_annotation_1"
        filepath: Path = tmp_path / f"{filename}.json"

        content: Dict[str, Any] = {
            "dataset": "cars",
            "image": {
                "width": 1000,
                "height": 1285,
                "original_filename": f"{filename}.jpeg",
                "filename": f"{filename}.jpeg",
                "path": "/",
            },
            "annotations": [{"bounding_box": {"h": 429.36, "w": 773.78, "x": 95.35, "y": 580.72}, "name": "car_bbox"}],
        }

        with open(filepath, "w") as output_file:
            json.dump(content, output_file)

        yield filepath

    @pytest.fixture
    def annotation_file_2(tmp_path: Path):
        filename = "bbox_annotation_2"
        filepath: Path = tmp_path / f"{filename}.json"

        content: Dict[str, Any] = {
            "dataset": "cars",
            "image": {
                "width": 1000,
                "height": 1285,
                "original_filename": f"{filename}.jpeg",
                "filename": f"{filename}.jpeg",
                "path": "/",
            },
            "annotations": [{"bounding_box": {"h": 400.00, "w": 700.00, "x": 90.00, "y": 580.00}, "name": "car_bbox"}],
        }

        with open(filepath, "w") as output_file:
            json.dump(content, output_file)

        yield filepath

    @pytest.fixture
    def annotation_file_3(tmp_path: Path):
        filename = "bbox_annotation_3"
        filepath: Path = tmp_path / f"{filename}.json"

        content: Dict[str, Any] = {
            "dataset": "cars",
            "image": {
                "width": 1000,
                "height": 1285,
                "original_filename": f"{filename}.jpeg",
                "filename": f"{filename}.jpeg",
                "path": "/",
            },
            "annotations": [
                {"bounding_box": {"h": 400.00, "w": 700.00, "x": 90.00, "y": 580.00}, "name": "car_bbox"},
                {"bounding_box": {"h": 500.00, "w": 800.00, "x": 91.00, "y": 581.00}, "name": "car_bbox"},
                {"bounding_box": {"h": 600.00, "w": 900.00, "x": 92.00, "y": 582.00}, "name": "car_bbox"},
            ],
        }

        with open(filepath, "w") as output_file:
            json.dump(content, output_file)

        yield filepath

    def it_creates_missing_folders(parser: ExportParser, folder_path: Path):
        export_annotations(parser, [], folder_path)
        assert folder_path.exists()

    def it_creates_txt_files_for_each_annotation(
        parser: ExportParser, folder_path: Path, annotation_file_1: Path, annotation_file_2: Path
    ):
        export_annotations(parser, [annotation_file_1, annotation_file_2], folder_path)

        txt_file_1: Path = Path(f"{annotation_file_1.stem}.txt")
        txt_file_2: Path = Path(f"{annotation_file_2.stem}.txt")

        assert Path(folder_path, txt_file_1).exists()
        assert Path(folder_path, txt_file_2).exists()

    def it_exports_file_contents_correctly(
        parser: ExportParser, folder_path: Path, annotation_file_1: Path, annotation_file_3: Path
    ):
        export_annotations(parser, [annotation_file_1, annotation_file_3], folder_path)

        txt_file_1: Path = Path(folder_path, f"{annotation_file_1.stem}.txt")
        txt_file_3: Path = Path(folder_path, f"{annotation_file_3.stem}.txt")

        content_file_1: Optional[str] = None
        with open(txt_file_1, "r") as f1:
            content_file_1 = f1.read()

        content_file_3: Optional[str] = None
        with open(txt_file_3, "r") as f3:
            content_file_3 = f3.read()

        assert txt_file_1.exists()
        assert txt_file_3.exists()

        assert content_file_1 == "car_bbox 95.35 580.72 773.78 429.36\n"
        assert (
            content_file_3
            == "car_bbox 90.0 580.0 700.0 400.0\ncar_bbox 91.0 581.0 800.0 500.0\ncar_bbox 92.0 582.0 900.0 600.0\n"
        )
