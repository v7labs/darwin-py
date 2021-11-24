from functools import partial
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest
from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile, Point
from darwin.importer.formats.labelbox import parse_file
from darwin.importer.formats.labelbox_schemas import labelbox_export
from jsonschema import ValidationError, validate


def describe_parse_file():
    @pytest.fixture
    def file_path(tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    @pytest.fixture
    def validator():
        validate_with_schema = partial(validate, schema=labelbox_export)
        yield validate_with_schema

    def test_it_returns_none_if_there_are_no_annotations(validator: Callable[[Any], None]):
        path = Path("path/to/file.xml")
        assert parse_file(path, validator) is None

    def test_it_raises_if_external_id_is_missing(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title":"Fruit",
                        "bbox":{
                           "top":3558,
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               }
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'External ID' is a required property" in str(error.value)

    def test_it_raises_if_label_is_missing(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [{"External ID": "flowers.jpg"}]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'Label' is a required propert" in str(error.value)

    def test_it_raises_if_label_objects_is_missing(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [{"External ID": "flowers.jpg", "Label": {}}]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'objects' is a required propert" in str(error.value)

    def test_it_raises_if_label_object_has_unknown_format(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [{
               "Label":{
                  "objects":[{"title":"Fruit", "unkown_annotation": 0}]
               },
               "External ID": "demo-image-7.jpg"
            }]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'point' is a required property" in str(error.value)

    def test_it_raises_if_annotation_has_no_title(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "bbox":{
                           "top":3558,
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'title' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_top(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title": "Fruit",
                        "bbox":{
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'top' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_left(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title": "Fruit",
                        "bbox":{
                           "top":3385,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'left' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_width(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title": "Fruit",
                        "bbox":{
                           "left":145,
                           "top":3385,
                           "height":623
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'width' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_height(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title": "Fruit",
                        "bbox":{
                           "left":145,
                           "top":3385,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'height' is a required property" in str(error.value)

    def test_it_imports_bbox_images(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title":"Fruit",
                        "bbox":{
                           "top":3558,
                           "left":145,
                           "height":623,
                           "width":449
                        }
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_file(file_path, validator)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations
        bbox_annotation = annotation_file.annotations.pop()
        assert_bbox(bbox_annotation, 145, 3558, 623, 449)

        annotation_class = bbox_annotation.annotation_class
        assert_annotation_class(annotation_class, "Fruit", "bounding_box")

    def test_it_raises_if_polygon_point_has_missing_x(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title": "Banana",
                        "polygon": [
                              {"x": 3665.814, "y": 351.628},
                              {"x": 3762.93, "y": 810.419},
                              {"y": 914.233}
                        ]
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'x' is a required property" in str(error.value)

    def test_it_raises_if_polygon_point_has_missing_y(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
         [
            {
               "Label":{
                  "objects":[
                     {
                        "title": "Banana",
                        "polygon": [
                              {"x": 3665.814, "y": 351.628},
                              {"x": 3762.93},
                              {"x": 3042.93, "y": 914.233}
                        ]
                     }
                  ]
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_file(file_path, validator)

        assert "'y' is a required property" in str(error.value)

    def test_it_imports_polygon_images(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Fish",
                           "polygon": [
                              {"x": 3665.814, "y": 351.628},
                              {"x": 3762.93, "y": 810.419},
                              {"x": 3042.93, "y": 914.233}
                           ]
                        }
                     ]
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_file(file_path, validator)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        polygon_annotation = annotation_file.annotations.pop()
        assert_polygon(
            polygon_annotation,
            [{"x": 3665.814, "y": 351.628}, {"x": 3762.93, "y": 810.419}, {"x": 3042.93, "y": 914.233}],
        )

        annotation_class = polygon_annotation.annotation_class
        assert_annotation_class(annotation_class, "Fish", "polygon")

    def test_it_imports_point_images(file_path: Path, validator: Callable[[Any], None]):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Dog",
                           "point": {"x": 342.93, "y": 914.233}
                        }
                     ]
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_file(file_path, validator)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        point_annotation = annotation_file.annotations.pop()
        assert_point(point_annotation, {"x": 342.93, "y": 914.233})

        annotation_class = point_annotation.annotation_class
        assert_annotation_class(annotation_class, "Dog", "keypoint")


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


def assert_annotation_class(
    annotation_class: AnnotationClass, name: str, type: str, internal_type: Optional[str] = None
) -> None:
    assert annotation_class
    assert annotation_class.name == name
    assert annotation_class.annotation_type == type
    assert annotation_class.annotation_internal_type == internal_type

