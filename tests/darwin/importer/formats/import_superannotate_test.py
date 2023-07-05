from pathlib import Path
from typing import Dict, List, Optional, cast

import pytest
from jsonschema import ValidationError

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    CuboidData,
    EllipseData,
    Point,
    SubAnnotation,
)
from darwin.importer.formats.superannotate import parse_path


class TestParsePath:
    @pytest.fixture
    def classes_file_path(self, tmp_path: Path):
        path = tmp_path / "classes.json"
        yield path
        path.unlink()

    @pytest.fixture
    def annotations_file_path(self, tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    def test_returns_none_if_file_is_not_json(self):
        bad_path = Path("/tmp/annotation.xml")
        assert parse_path(bad_path) is None

    def test_returns_none_if_file_is_classes(self):
        bad_path = Path("/tmp/classes.json")
        assert parse_path(bad_path) is None

    def test_raises_if_folder_has_no_classes_file(self, annotations_file_path: Path):
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

    def test_returns_empty_file_if_there_are_no_annotations(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [],
            "tags": [],
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

    def test_raises_if_annotation_has_no_type(self, annotations_file_path: Path, classes_file_path: Path):
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

    def test_raises_if_annotation_has_no_class_id(self, annotations_file_path: Path, classes_file_path: Path):
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

    def test_raises_if_metadata_is_missing(self, annotations_file_path: Path, classes_file_path: Path):
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

    def test_raises_if_metadata_is_missing_name(self, annotations_file_path: Path, classes_file_path: Path):
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

    def test_raises_if_point_has_missing_coordinate(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
          {
             "instances": [
                {
                   "type": "point",
                   "y": 0
                }
             ],
             "tags": [],
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

        error_str = str(error.value)
        assert all(["point" in error_str, "ellipse" in error_str])

    def test_imports_point_vectors(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
       {
          "instances": [
             {"type": "point", "x": 1.93, "y": 0.233, "classId": 1, "attributes": []}
          ],
          "tags": [],
         "metadata": {"name": "demo-image-0.jpg"}
       }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1, "attribute_groups": []}
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
        assert_annotation_class(annotation_class, "Person-point", "keypoint")

    def test_raises_if_ellipse_has_missing_coordinate(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
          {
             "instances": [
                {"type": "ellipse", "cy": 0, "cx": 0, "rx": 0, "angle": 0}
             ],
             "tags": [],
             "metadata": {"name": "demo-image-0.jpg"}
          }
         """
        classes_json: str = """[]"""
        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_path(annotations_file_path)

        error_str = str(error.value)
        assert all(["ellipse" in error_str, "point" in error_str])

    def test_imports_ellipse_vectors(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "ellipse",
                  "classId": 1,
                  "cx": 922.1,
                  "cy": 475.8,
                  "rx": 205.4,
                  "ry": 275.7,
                  "angle": 0,
                  "attributes": []
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1, "attribute_groups": []}
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

        ellipse_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_ellipse(
            ellipse_annotation, {"angle": 0, "center": {"x": 922.1, "y": 475.8}, "radius": {"x": 205.4, "y": 275.7}}
        )

        annotation_class = ellipse_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person-ellipse", "ellipse")

    def test_raises_if_cuboid_has_missing_point(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
          {
             "instances": [
                {
                  "type": "cuboid",
                  "classId": 1,
                  "points": {
                     "f2": {"x": 3023.31, "y": 2302.75},
                     "r1": {"x": 1826.19, "y": 1841.44},
                     "r2": {"x": 2928, "y": 2222.69}
                  }
               }
             ],
             "tags": [],
             "metadata": {"name": "demo-image-0.jpg"}
          }
         """
        classes_json: str = """[]"""
        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_path(annotations_file_path)
        error_str = str(error.value)
        assert all(["cuboid" in error_str, "point" in error_str])

    def test_imports_cuboid_vectors(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "attributes": [],
                  "type": "cuboid",
                  "classId": 1,
                  "points": {
                     "f1": {"x": 1742.31, "y": 1727.06},
                     "f2": {"x": 3023.31, "y": 2302.75},
                     "r1": {"x": 1826.19, "y": 1841.44},
                     "r2": {"x": 2928, "y": 2222.69}
                  }
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1, "attribute_groups": []}
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

        cuboid_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_cuboid(
            cuboid_annotation,
            {
                "back": {"h": 381.25, "w": 1101.81, "x": 1826.19, "y": 1841.44},
                "front": {"h": 575.69, "w": 1281.0, "x": 1742.31, "y": 1727.06},
            },
        )

        annotation_class = cuboid_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person-cuboid", "cuboid")

    def test_raises_if_polygon_has_missing_points(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
          {
            "instances": [
               {
                  "type": "polygon",
                  "classId": 1
               }
            ],
            "tags": [],
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

        error_str = str(error.value)
        assert all(["polygon" in error_str, "point" in error_str])

    def test_imports_polygon_vectors(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "attributes": [],
                  "type": "polygon",
                  "classId": 1,
                  "points": [1053, 587.2, 1053.1, 586, 1053.8, 585.4]
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1, "attribute_groups": []}
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

        polygon_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_polygon(
            polygon_annotation,
            [{"x": 1053, "y": 587.2}, {"x": 1053.1, "y": 586}, {"x": 1053.8, "y": 585.4}],
        )

        annotation_class = polygon_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person-polygon", "polygon")

    def test_raises_if_polyline_has_missing_points(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
          {
            "instances": [
               {
                  "type": "polyline",
                  "classId": 1
               }
            ],
            "tags": [],
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

        error_str = str(error.value)
        assert all(["polyline" in error_str, "point" in error_str])

    def test_imports_polyline_vectors(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "attributes": [],
                  "type": "polyline",
                  "classId": 1,
                  "points": [1053, 587.2, 1053.1, 586, 1053.8, 585.4]
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1, "attribute_groups": []}
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

        line_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_line(
            line_annotation,
            [{"x": 1053, "y": 587.2}, {"x": 1053.1, "y": 586}, {"x": 1053.8, "y": 585.4}],
        )

        annotation_class = line_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person-polyline", "line")

    def test_raises_if_bbox_has_missing_points(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
          {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x2": 1920, "y1": 516.5, "y2": 734}
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
         """
        classes_json: str = """[]"""
        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_path(annotations_file_path)

        error_str = str(error.value)
        assert all(["bbox" in error_str, "point" in error_str])

    def test_imports_bbox_vectors(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x1": 1642.9, "x2": 1920, "y1": 516.5, "y2": 734},
                  "attributes": []
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
          {"name": "Person", "id": 1, "attribute_groups": []}
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

        bbox_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_bbox(bbox_annotation, 1642.9, 516.5, 217.5, 277.1)

        annotation_class = bbox_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person-bbox", "bounding_box")

    def test_raises_if_an_attributes_is_missing(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x1": 1642.9, "x2": 1920, "y1": 516.5, "y2": 734}
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
         {
            "attribute_groups": [
                  {
                     "id": 1,
                     "name": "Sex",
                     "attributes": [
                        {"id": 1, "name": "Male"}
                     ]
                  }
            ],
            "id": 1,
            "name": "Person"
         }
      ]
       """

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_path(annotations_file_path)

        error_str = str(error.value)
        assert all(["type" in error_str, "bbox" in error_str])

    def test_raises_if_an_attribute_from_a_group_is_missing(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x1": 1642.9, "x2": 1920, "y1": 516.5, "y2": 734},
                  "attributes": [{"id": 2, "groupId": 1}]
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
         {
            "attribute_groups": [
                  {
                     "id": 1,
                     "name": "Sex",
                     "attributes": [
                        {"id": 1, "name": "Male"}
                     ]
                  }
            ],
            "id": 1,
            "name": "Person"
         }
      ]
       """

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValueError) as error:
            parse_path(annotations_file_path)

        assert "No attribute data found for {'id': 2, 'groupId': 1}." in str(error.value)

    def test_imports_attributes(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x1": 1642.9, "x2": 1920, "y1": 516.5, "y2": 734},
                  "attributes": [{"id": 2, "groupId": 1}, {"id": 3, "groupId": 2}]
               }
            ],
            "tags": [],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
         {
            "attribute_groups": [
                  {
                     "id": 1,
                     "name": "Sex",
                     "attributes": [
                        {"id": 1, "name": "Male"},
                        {"id": 2, "name": "Female"}
                     ]
                  },
                  {
                     "id": 2,
                     "name": "Emotion",
                     "attributes": [
                        {"id": 3, "name": "Smiling"},
                        {"id": 4, "name": "Sadness"},
                        {"id": 5, "name": "Crying"}
                     ]
                  }
            ],
            "id": 1,
            "name": "Person"
         }
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

        bbox_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_bbox(bbox_annotation, 1642.9, 516.5, 217.5, 277.1)

        annotation_class = bbox_annotation.annotation_class
        assert_annotation_class(annotation_class, "Person-bbox", "bounding_box")

        assert_subannotations(bbox_annotation.subs, [SubAnnotation("attributes", ["Sex:Female", "Emotion:Smiling"])])

    def test_raises_if_tags_is_missing(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x1": 1642.9, "x2": 1920, "y1": 516.5, "y2": 734},
                  "attributes": []
               }
            ],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
         {"attribute_groups": [], "id": 1, "name": "Person"}
      ]
       """

        annotations_file_path.write_text(annotations_json)
        classes_file_path.write_text(classes_json)

        with pytest.raises(ValidationError) as error:
            parse_path(annotations_file_path)

        assert "'tags' is a required property" in str(error.value)

    def test_imports_tags(self, annotations_file_path: Path, classes_file_path: Path):
        annotations_json: str = """
         {
            "instances": [
               {
                  "type": "bbox",
                  "classId": 1,
                  "points": {"x1": 1642.9, "x2": 1920, "y1": 516.5, "y2": 734},
                  "attributes": []
               }
            ],
            "tags": ["street", "night"],
            "metadata": {"name": "demo-image-0.jpg"}
         }
      """
        classes_json: str = """
       [
         {
            "attribute_groups": [],
            "id": 1,
            "name": "Person"
         }
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

        street_tag: Annotation = cast(Annotation, annotation_file.annotations[1])
        assert_annotation_class(street_tag.annotation_class, "street", "tag")

        night_tag: Annotation = cast(Annotation, annotation_file.annotations[2])
        assert_annotation_class(night_tag.annotation_class, "night", "tag")


def assert_cuboid(annotation: Annotation, cuboid: CuboidData) -> None:
    cuboid_back: Dict[str, float] = cast(Dict[str, float], cuboid.get("back"))
    cuboid_front: Dict[str, float] = cast(Dict[str, float], cuboid.get("front"))

    data = annotation.data
    assert data

    back = data.get("back")
    assert back
    assert back.get("x") == cuboid_back.get("x")
    assert back.get("y") == cuboid_back.get("y")
    assert back.get("h") == cuboid_back.get("h")
    assert back.get("w") == cuboid_back.get("w")

    front = data.get("front")
    assert front
    assert front.get("x") == cuboid_front.get("x")
    assert front.get("y") == cuboid_front.get("y")
    assert front.get("h") == cuboid_front.get("h")
    assert front.get("w") == cuboid_front.get("w")


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


def assert_ellipse(annotation: Annotation, ellipse: EllipseData) -> None:
    ellipse_center: Dict[str, float] = cast(Dict[str, float], ellipse.get("center"))
    ellipse_radius: Dict[str, float] = cast(Dict[str, float], ellipse.get("radius"))

    data = annotation.data
    assert data
    assert data.get("angle") == ellipse.get("angle")

    center = data.get("center")
    assert center
    assert center.get("x") == ellipse_center.get("x")
    assert center.get("y") == ellipse_center.get("y")

    radius = data.get("radius")
    assert radius
    assert radius.get("x") == ellipse_radius.get("x")
    assert radius.get("y") == ellipse_radius.get("y")


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
