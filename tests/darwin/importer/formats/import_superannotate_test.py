from functools import partial
from pathlib import Path
from typing import Any, Callable, List, Optional, cast

import pytest
from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    Point,
    SubAnnotation,
)
from darwin.importer.formats.superannotate import parse_file
from darwin.importer.formats.superannotate_schemas import (
    classes_export,
    superannotate_export,
)
from jsonschema import ValidationError, validate


def describe_parse_file():
    @pytest.fixture
    def annotations_file_path(tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    @pytest.fixture
    def classes_file_path(tmp_path: Path):
        path = tmp_path / "classes.json"
        yield path
        path.unlink()

    @pytest.fixture
    def validate_annotations():
        validate_with_schema = partial(validate, schema=superannotate_export)
        yield validate_with_schema

    @pytest.fixture
    def validate_classes():
        validate_with_schema = partial(validate, schema=classes_export)
        yield validate_with_schema

    def it_returns_none_if_annotations_file_has_wrong_extension(
        validate_annotations: Callable[[Any], None], validate_classes: Callable[[Any], None]
    ):
        annotations_file_path = Path("path/to/file.xml")
        classes_file_path = Path("path/to/classes.json")
        assert parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes) is None

    def it_returns_none_if_classes_file_has_wrong_extension(
        validate_annotations: Callable[[Any], None], validate_classes: Callable[[Any], None]
    ):
        annotations_file_path = Path("path/to/file.json")
        classes_file_path = Path("path/to/classes.xml")
        assert parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes) is None

    def it_returns_empty_if_there_are_no_annotations(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):
        annotations_json: str = """
         {
            "instances": [],
            "metadata": {
               "name": "demo-image-0.jpg"
            }
         }
         """
        classes_json: str = """[]"""

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        assert parse_file(
            annotations_file_path, classes_file_path, validate_annotations, validate_classes
        ) == AnnotationFile(
            annotations=[],
            path=annotations_file_path,
            filename="demo-image-0.jpg",
            annotation_classes=set(),
            remote_path="/",
        )

    def it_raises_if_annotation_has_no_type(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):
        annotations_json: str = """
          {
             "instances": [
                {
                   "x": 1,
                   "y": 0
                }
             ],
             "metadata": {
                "name": "demo-image-0.jpg"
             }
          }
         """
        classes_json: str = """[]"""

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes)

            assert "'type' is a required property" in str(error.value)

    def it_raises_if_annotation_has_no_class_id(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):
        annotations_json: str = """
          {
             "instances": [
                {
                   "type": "point",
                   "x": 1,
                   "y": 0
                }
             ],
             "metadata": {
                "name": "demo-image-0.jpg"
             }
          }
         """
        classes_json: str = """[]"""

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes)

            assert "'classId' is a required property" in str(error.value)

    def it_raises_if_metadata_is_missing(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):
        annotations_json: str = """
          {
             "instances": [
                {
                   "type": "point",
                   "x": 1,
                   "y": 0
                }
             ]
          }
         """
        classes_json: str = """[]"""

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes)

            assert "'metadata' is a required property" in str(error.value)

    def it_raises_if_metadata_is_missing_name(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):
        annotations_json: str = """
          {
             "instances": [
                {
                   "type": "point",
                   "x": 1,
                   "y": 0
                }
             ],
             "metadata": { }
          }
         """
        classes_json: str = """[]"""
        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes)

            assert "'name' is a required property" in str(error.value)

    def it_raises_if_point_has_missing_coordinate(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):
        annotations_json: str = """
          {
             "instances": [
                {
                   "type": "point",
                   "y": 0
                }
             ],
             "metadata": {
                "name": "demo-image-0.jpg"
             }
          }
         """
        classes_json: str = """[]"""
        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_file(annotations_file_path, classes_file_path, validate_annotations, validate_classes)

        assert "'x' is a required property" in str(error.value)

    def it_imports_point_vectors(
        annotations_file_path: Path,
        classes_file_path: Path,
        validate_annotations: Callable[[Any], None],
        validate_classes: Callable[[Any], None],
    ):

        annotations_json: str = """
       {
          "instances": [
             {
                "type": "point",
                "x": 1.93,
                "y": 0.233,
                "classId": 1
             }
          ],
         "metadata": {
            "name": "demo-image-0.jpg"
         }
       }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1}
       ]
       """

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        annotation_file: Optional[AnnotationFile] = parse_file(
            annotations_file_path, classes_file_path, validate_annotations, validate_classes
        )
        assert annotation_file is not None
        assert annotation_file.path == annotations_file_path
        assert annotation_file.filename == "demo-image-0.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        point_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_point(point_annotation, {"x": 1.93, "y": 0.233})

        annotation_class = point_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person", "keypoint")


def assert_bbox(annotation: Annotation, x: float, y: float, h: float, w: float) -> None:
    data = annotation.data

    assert data
    assert data.get("x") == x
    assert data.get("y") == y
    assert data.get("w") == w
    assert data.get("h") == h


def assert_polygon(annotation: Annotation, points: List[Point]) -> None:
    actual_points = annotation.data.get("path")
    assert actual_points
    assert actual_points == points


def assert_point(annotation: Annotation, point: Point) -> None:
    data = annotation.data
    assert data
    assert data.get("x") == point.get("x")
    assert data.get("y") == point.get("y")


def assert_line(annotation: Annotation, line: List[Point]) -> None:
    actual_line = annotation.data.get("path")
    assert actual_line
    assert actual_line == line


def assert_annotation_class(
    annotation_class: AnnotationClass, name: str, type: str, internal_type: Optional[str] = None
) -> None:
    assert annotation_class
    assert annotation_class.name == name
    assert annotation_class.annotation_type == type
    assert annotation_class.annotation_internal_type == internal_type


def assert_subannotations(actual_subs: List[SubAnnotation], expected_subs: List[SubAnnotation]) -> None:
    assert actual_subs
    for actual_sub in actual_subs:
        for expected_sub in expected_subs:
            assert actual_sub.annotation_type == expected_sub.annotation_type
            assert actual_sub.data == expected_sub.data

