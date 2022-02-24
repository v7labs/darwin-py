import shutil
from pathlib import Path
from typing import Dict, Optional

import pytest
from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats import yolo


def describe_export():
    @pytest.fixture
    def folder_path(tmp_path: Path):
        path: Path = tmp_path / "yolo_export_output_files"
        yield path
        shutil.rmtree(path)

    def test_it_creates_missing_folders(folder_path: Path):
        yolo.export([], folder_path)
        assert folder_path.exists()

    def it_creates_txt_files_for_each_image(folder_path: Path):
        annotation_file_1 = _create_empty_annotation_file("annotation_test_1")
        annotation_file_2 = _create_empty_annotation_file("annotation_test_2")

        yolo.export([annotation_file_1, annotation_file_2], folder_path)

        txt_file_1: Path = Path(f"{Path(annotation_file_1.filename).stem}.txt")
        txt_file_2: Path = Path(f"{Path(annotation_file_2.filename).stem}.txt")

        assert Path(folder_path, txt_file_1).exists()
        assert Path(folder_path, txt_file_2).exists()

    def it_converts_darwin_bounding_boxes(folder_path: Path):
        bbox = {"x": 91.59, "y": 432.26, "w": 1716.06, "h": 556.88}
        annotation_file = _create_bbox_annotation_file("car", bbox)

        yolo.export([annotation_file], folder_path)

        txt_file: Path = Path(folder_path, f"{Path(annotation_file.filename).stem}.txt")
        with open(txt_file) as f:
            lines = f.readlines()
            assert lines[0] == "car 91.59 432.26 1716.06 556.88"


# def it_converts_prints_error_if_given_video_annotation(folder_path: Path):

#     def it_converts_darwin_polygons():

#     def it_converts_darwin_complex_polygons():

#     def it_converts_darwin_ellipses():


def _create_empty_annotation_file(filename: str) -> AnnotationFile:
    return AnnotationFile(
        path=Path(f"/{filename}.json"),
        filename=f"{filename}.jpg",
        annotation_classes=set(),
        annotations=[],
        frame_urls=None,
        image_height=1080,
        image_width=1920,
        is_video=False,
    )


def _create_bbox_annotation_file(
    class_name: str, bbox: Dict[str, float], filename: Optional[str] = "annotation_test"
) -> AnnotationFile:
    annotation_class: AnnotationClass = AnnotationClass(
        name=class_name, annotation_type="bounding_box", annotation_internal_type=None
    )
    annotation = Annotation(
        annotation_class=annotation_class,
        data={
            "path": [{...}],
            "bounding_box": bbox,
        },
        subs=[],
    )
    return AnnotationFile(
        path=Path(f"/{filename}.json"),
        filename=f"{filename}.jpg",
        annotation_classes={annotation_class},
        annotations=[annotation],
        frame_urls=None,
        image_height=1080,
        image_width=1920,
        is_video=False,
    )
