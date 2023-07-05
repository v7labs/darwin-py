import shutil
from pathlib import Path

import pytest

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.yolo import export


class TestDescribeExport:
    @pytest.fixture
    def folder_path(self, tmp_path: Path):
        path: Path = tmp_path / "yolo_export_output_files"
        yield path
        shutil.rmtree(path)

    def test_it_creates_missing_folders(self, folder_path: Path):
        annotation_class: AnnotationClass = AnnotationClass(
            name="car", annotation_type="polygon", annotation_internal_type=None
        )
        bbox = {"x": 94.0, "y": 438.0, "w": 1709.0, "h": 545.0}
        annotation = Annotation(
            annotation_class=annotation_class,
            data={
                "path": [{...}],
                "bounding_box": bbox,
            },
            subs=[],
        )
        annotation_file = AnnotationFile(
            path=Path("/annotation_test.json"),
            filename="annotation_test.jpg",
            annotation_classes={annotation_class},
            annotations=[annotation],
            frame_urls=None,
            image_height=1080,
            image_width=1920,
            is_video=False,
        )

        export([annotation_file], folder_path)
        assert folder_path.exists()

        files = list(folder_path.glob("*"))

        assert (folder_path / "annotation_test.txt") in files
        assert (folder_path / "darknet.labels") in files

        yolo_lines = (folder_path / "annotation_test.txt").read_text().split("\n")
        assert yolo_lines[0] == "0 {} {} {} {}".format(
            (bbox["x"] + bbox["w"] / 2) / 1920, (bbox["y"] + bbox["h"] / 2) / 1080, bbox["w"] / 1920, bbox["h"] / 1080
        )

        yolo_classes = (folder_path / "darknet.labels").read_text().split("\n")
        assert yolo_classes[0] == "car"
