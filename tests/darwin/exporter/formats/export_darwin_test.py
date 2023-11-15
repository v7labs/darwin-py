from pathlib import Path

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile
from darwin.exporter.formats.darwin import build_image_annotation


def test_empty_annotation_file():
    annotation_file = AnnotationFile(
        path=Path("test.json"),
        filename="test.json",
        annotation_classes=[],
        annotations=[],
    )

    assert build_image_annotation(annotation_file) == {
        "annotations": [],
        "image": {"filename": "test.json", "height": None, "url": None, "width": None},
    }


def test_complete_annotation_file():
    annotation_class = AnnotationClass(name="test", annotation_type="polygon")
    annotation = Annotation(
        annotation_class=annotation_class, data={"path": []}, subs=[]
    )

    annotation_file = AnnotationFile(
        path=Path("test.json"),
        filename="test.json",
        annotation_classes=[annotation_class],
        annotations=[annotation],
        image_height=1080,
        image_width=1920,
        image_url="https://darwin.v7labs.com/image.jpg",
    )

    assert build_image_annotation(annotation_file) == {
        "annotations": [{"name": "test", "polygon": {"path": []}}],
        "image": {
            "filename": "test.json",
            "height": 1080,
            "url": "https://darwin.v7labs.com/image.jpg",
            "width": 1920,
        },
    }
