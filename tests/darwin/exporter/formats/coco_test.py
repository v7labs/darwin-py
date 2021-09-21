from pathlib import Path

import darwin.datatypes as dt
import pytest
from darwin.exporter.formats import coco


def describe_build_annotation():
    @pytest.fixture
    def annotation_file() -> dt.AnnotationFile:
        return dt.AnnotationFile(path=Path("test.json"), filename="test.json", annotation_classes=set(), annotations=[])

    def polygon_include_extras(annotation_file: dt.AnnotationFile):
        polygon = dt.Annotation(
            dt.AnnotationClass("polygon_class", "polygon"),
            {"path": [{"x": 1, "y": 1}, {"x": 2, "y": 2}, {"x": 1, "y": 2}]},
            [dt.make_instance_id(1)],
        )

        categories = {"polygon_class": 1}

        assert coco.build_annotation(annotation_file, "test-id", polygon, categories)["extra"] == {"instance_id": 1}

    def bounding_boxes_include_extras(annotation_file: dt.AnnotationFile):
        bbox = dt.Annotation(
            dt.AnnotationClass("bbox_class", "bounding_box"),
            {"x": 1, "y": 1, "w": 5, "h": 5},
            [dt.make_instance_id(1)],
        )

        categories = {"bbox_class": 1}

        assert coco.build_annotation(annotation_file, "test-id", bbox, categories)["extra"] == {"instance_id": 1}
