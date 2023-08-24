from pathlib import Path
from typing import List

import pytest

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.yolo_segmented import CLOSE_VERTICES, export


@pytest.fixture
def annotation_classes() -> List[AnnotationClass]:
    return [
        AnnotationClass(name="class1", annotation_type="bounding_box"),
        AnnotationClass(name="class2", annotation_type="polygon"),
        AnnotationClass(name="class3", annotation_type="polygon"),
    ]


@pytest.fixture
def annotations(annotation_classes: List[AnnotationClass]) -> List[Annotation]:
    return [
        # fmt: off
        Annotation(
            annotation_class=annotation_classes[0],
            data={
                #bounding box
                "h": 130,
                "w": 250,
                "x": 20,
                "y": 30,
            },
            subs=[],
            slot_names=[
                "0",
            ],
        ),
        Annotation(
            annotation_class=annotation_classes[1],
            data={
                # Polygon
                "path": [
                    { "x": 0, "y": 0, },
                    { "x": 0, "y": 100, },
                    { "x": 50, "y": 150, },
                    { "x": 100, "y": 100, },
                    { "x": 0, "y": 100, },
                    { "x": 0, "y": 0 },
                ]
            },
            subs=[],
            slot_names=[
                "1",
            ],
        ),
        # Unexpected case we should still handle
        Annotation(
            annotation_class=annotation_classes[2],
            data={
                # Polygon
                "points": [
                    { "x": 0, "y": 0, },
                    { "x": 0, "y": 100, },
                    { "x": 50, "y": 150, },
                    { "x": 100, "y": 100, },
                    { "x": 0, "y": 100, },
                    { "x": 0, "y": 0 },
                ]
            },
            subs=[],
            slot_names=[
                "1",
            ],
        ),
        # fmt: on
    ]


@pytest.fixture
def annotation_files(annotation_classes: List[AnnotationClass], annotations: List[Annotation]) -> List[AnnotationFile]:
    return [
        # fmt: off
        AnnotationFile(
            path=Path("/tmp/tests/file1.json"),
            filename="file1.json",
            annotation_classes=set(annotation_classes),
            annotations=annotations,
            image_height=1000,
            image_width=1000,
        )
        # fmt: on
    ]


def test_export_yolo_segmented(annotation_files: List[AnnotationFile], tmp_path: Path) -> None:
    export(annotation_files, tmp_path)
    assert (tmp_path / "darknet.labels").exists()
    assert (tmp_path / "file1.txt").exists()

    output_lines = (tmp_path / "file1.txt").read_text().splitlines()
    if CLOSE_VERTICES:
        assert output_lines[0] == "0 0.02 0.03 0.27 0.03 0.27 0.16 0.02 0.16 0.02 0.03"
        assert output_lines[1] == "1 0.0 0.0 0.0 0.1 0.05 0.15 0.1 0.1 0.0 0.1 0.0 0.0 0.0 0.0"
        assert output_lines[2] == "2 0.0 0.0 0.0 0.1 0.05 0.15 0.1 0.1 0.0 0.1 0.0 0.0 0.0 0.0"
    else:
        assert output_lines[0] == "0 0.02 0.03 0.27 0.03 0.27 0.16 0.02 0.16"
        assert output_lines[1] == "1 0.0 0.0 0.0 0.1 0.05 0.15 0.1 0.1 0.0 0.1 0.0 0.0"
        assert output_lines[2] == "2 0.0 0.0 0.0 0.1 0.05 0.15 0.1 0.1 0.0 0.1 0.0 0.0"
