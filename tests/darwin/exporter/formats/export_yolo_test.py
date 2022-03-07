from pathlib import Path
from typing import Dict, Optional, Tuple

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    ConversionError,
)
from darwin.exporter.formats import yolo
from darwin.exporter.formats.yolo import YoloAnnotation


def describe_export():
    #     def it_converts_darwin_polygons():

    #     def it_converts_darwin_complex_polygons():

    #     def it_converts_darwin_ellipses():

    def it_converts_darwin_bounding_boxes():
        bbox = {"x": 91.59, "y": 432.26, "w": 1716.06, "h": 556.88}
        annotation_file = _create_bbox_annotation_file("car", bbox)

        result = yolo.export([annotation_file])

        assert result.conversions == [
            YoloAnnotation(
                annotation_class="car",
                x=91.59,
                y=432.26,
                width=1716.06,
                height=556.88,
                file=Path("annotation_test.txt"),
            )
        ]
        assert result.errors == []

    def it_returns_empty_if_nothing_can_be_converted():
        annotation_file = _create_empty_annotation_file("empty")

        result = yolo.export([annotation_file])

        assert result.conversions == []
        assert result.errors == []

    def it_returns_error_if_a_conversion_failed():
        bad_annotation, bad_annotation_file = _create_bad_annotation_file("super-mega-poly-bbox")

        result = yolo.export([bad_annotation_file])

        assert result.conversions == []
        assert result.errors == [
            ConversionError(
                reason="Unsupported annotation type: super-mega-poly-bbox",
                annotation=bad_annotation,
                filename=Path("/annotation_test.json"),
            )
        ]


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
        data=bbox,
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


def _create_bad_annotation_file(
    bad_annotation: str, filename: Optional[str] = "annotation_test"
) -> Tuple[Annotation, AnnotationFile]:
    annotation_class: AnnotationClass = AnnotationClass(
        name="", annotation_type=bad_annotation, annotation_internal_type=None
    )
    annotation = Annotation(
        annotation_class=annotation_class,
        data={
            "path": [{...}],
        },
        subs=[],
    )

    annotation_file = AnnotationFile(
        path=Path(f"/{filename}.json"),
        filename=f"{filename}.jpg",
        annotation_classes={annotation_class},
        annotations=[annotation],
        frame_urls=None,
        image_height=1080,
        image_width=1920,
        is_video=False,
    )

    return annotation, annotation_file
