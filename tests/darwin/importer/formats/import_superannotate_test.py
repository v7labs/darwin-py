from pathlib import Path
from typing import List, Optional, cast

import pytest
from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    Point,
    SubAnnotation,
)
from darwin.importer.formats.superannotate import parse_path
from jsonschema import ValidationError


def describe_parse_path():
    @pytest.fixture
    def classes_file_path(tmp_path: Path):
        path = tmp_path / "classes.json"
        yield path
        path.unlink()

    @pytest.fixture
    def annotations_file_path(tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    def it_returns_none_if_file_is_not_json():
        bad_path = Path("/tmp/annotation.xml")
        assert parse_path(bad_path) is None

    def it_returns_none_if_file_is_classes():
        bad_path = Path("/tmp/classes.json")
        assert parse_path(bad_path) is None

    def it_raises_if_folder_has_no_classes_file(annotations_file_path: Path):
        annotations_json: str = """
         {
            "instances": [],
            "metadata": {
               "name": "demo-image-0.jpg"
            }
         }
         """
        annotations_file_path.write_text(annotations_json)

        with pytest.raises(ValueError) as error:
            parse_path(annotations_file_path)

        assert "Folder must contain a 'classes.json'" in str(error.value)

    def it_returns_empty_file_if_there_are_no_annotations(annotations_file_path: Path, classes_file_path: Path):
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

        assert parse_path(annotations_file_path) == AnnotationFile(
            annotations=[],
            path=annotations_file_path,
            filename="demo-image-0.jpg",
            annotation_classes=set(),
            remote_path="/",
        )

    def it_raises_if_annotation_has_no_type(annotations_file_path: Path, classes_file_path: Path):
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
            parse_path(annotations_file_path)

            assert "'type' is a required property" in str(error.value)

    def it_raises_if_annotation_has_no_class_id(annotations_file_path: Path, classes_file_path: Path):
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
            parse_path(annotations_file_path)

            assert "'classId' is a required property" in str(error.value)

    def it_raises_if_metadata_is_missing(annotations_file_path: Path, classes_file_path: Path):
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
            parse_path(annotations_file_path)

            assert "'metadata' is a required property" in str(error.value)

    def it_raises_if_metadata_is_missing_name(annotations_file_path: Path, classes_file_path: Path):
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
            parse_path(annotations_file_path)

            assert "'name' is a required property" in str(error.value)

    def it_raises_if_point_has_missing_coordinate(annotations_file_path: Path, classes_file_path: Path):
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
            parse_path(annotations_file_path)

        assert "'x' is a required property" in str(error.value)

    def it_imports_point_vectors(annotations_file_path: Path, classes_file_path: Path):

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

        annotation_file: Optional[AnnotationFile] = parse_path(annotations_file_path)
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

