from pathlib import Path
from typing import List, Optional, cast

import pytest
from jsonschema import ValidationError

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    Point,
    SubAnnotation,
)
from darwin.importer.formats.labelbox import parse_path


def describe_parse_path():
    @pytest.fixture
    def file_path(tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    def test_it_returns_none_if_there_are_no_annotations():
        path = Path("path/to/file.xml")
        assert parse_path(path) is None

    def test_it_raises_if_external_id_is_missing(file_path: Path):
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
            parse_path(file_path)

        assert "'External ID' is a required property" in str(error.value)

    def test_it_raises_if_label_is_missing(file_path: Path):
        json: str = """
         [{"External ID": "flowers.jpg"}]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'Label' is a required propert" in str(error.value)

    def test_it_raises_if_label_objects_is_missing(file_path: Path):
        json: str = """
         [{"External ID": "flowers.jpg", "Label": {}}]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'objects' is a required property" in str(error.value)

    def test_it_raises_if_label_object_has_unknown_format(file_path: Path):
        json: str = """
         [{
               "Label":{
                  "objects":[{"title":"Fruit", "unkown_annotation": 0}],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "is not valid under any of the given schemas" in str(error.value)
        assert "oneOf" in str(error.value)

    def test_it_raises_if_annotation_has_no_title(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'title' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_top(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'top' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_left(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'left' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_width(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'width' is a required property" in str(error.value)

    def test_it_raises_if_bbox_has_missing_height(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'height' is a required property" in str(error.value)

    def test_it_imports_bbox_images(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations
        bbox_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_bbox(bbox_annotation, 145, 3558, 623, 449)

        annotation_class = bbox_annotation.annotation_class
        assert_annotation_class(annotation_class, "Fruit", "bounding_box")

    def test_it_raises_if_polygon_point_has_missing_x(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'x' is a required property" in str(error.value)

    def test_it_raises_if_polygon_point_has_missing_y(file_path: Path):
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
                  ],
                  "classifications": []
               },
               "External ID": "demo-image-7.jpg"
            }
         ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'y' is a required property" in str(error.value)

    def test_it_imports_polygon_images(file_path: Path):
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
                     ],
                     "classifications": []
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        polygon_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_polygon(
            polygon_annotation,
            [{"x": 3665.814, "y": 351.628}, {"x": 3762.93, "y": 810.419}, {"x": 3042.93, "y": 914.233}],
        )

        annotation_class = polygon_annotation.annotation_class
        assert_annotation_class(annotation_class, "Fish", "polygon")

    def test_it_imports_point_images(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Dog",
                           "point": {"x": 342.93, "y": 914.233}
                        }
                     ],
                     "classifications": []
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        point_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_point(point_annotation, {"x": 342.93, "y": 914.233})

        annotation_class = point_annotation.annotation_class
        assert_annotation_class(annotation_class, "Dog", "keypoint")

    def test_it_imports_polyline_images(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Lion",
                           "line": [
                              {"x": 198.027, "y": 1979.196},
                              {"x": 321.472, "y": 1801.743},
                              {"x": 465.491, "y": 1655.152}
                           ]
                        }
                     ],
                     "classifications": []
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-7.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        line_annotation: Annotation = cast(Annotation, annotation_file.annotations.pop())
        assert_line(
            line_annotation,
            [{"x": 198.027, "y": 1979.196}, {"x": 321.472, "y": 1801.743}, {"x": 465.491, "y": 1655.152}],
        )

        annotation_class = line_annotation.annotation_class
        assert_annotation_class(annotation_class, "Lion", "line")

    def test_it_raises_if_classification_is_missing(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Kangaroo",
                           "point": {"x": 198.027, "y": 1979.196}
                        }
                     ]
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "'classifications' is a required property" in str(error.value)

    def test_it_raises_if_classification_object_has_no_answer(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Pig",
                           "point": {"x": 198.027, "y": 1979.196}
                        }
                     ],
                     "classifications": [
                        {
                           "value": "r_c_or_l_side_radiograph"
                        }
                     ]
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        assert "is not valid under any of the given schemas" in str(
            error.value
        ) or "'answer' is a required property" not in str(error.value)
        assert "oneOf" in str(error.value)

    def test_it_raises_if_classification_answer_has_no_value(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Pig",
                           "point": {"x": 198.027, "y": 1979.196}
                        }
                     ],
                     "classifications": [
                        {
                           "value": "r_c_or_l_side_radiograph",
                           "answer": {}
                        }
                     ]
                  },
                  "External ID": "demo-image-7.jpg"
               }
            ]
        """

        file_path.write_text(json)

        with pytest.raises(ValidationError) as error:
            parse_path(file_path)

        # The library asserts agains both types and if all fail, it prints the error of the
        # first type only.
        error_str = str(error.value)
        assert all(["{}" in error_str, "string" in error_str])

    def test_it_imports_classification_from_radio_buttons(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Worm",
                           "point": {"x": 342.93, "y": 914.233}
                        }
                     ],
                     "classifications": [
                        {
                           "value": "r_c_or_l_side_radiograph",
                           "answer": {"value": "right"}
                        }
                     ]
                  },
                  "External ID": "demo-image-9.jpg"
               }
            ]
        """

        file_path.write_text(json)
        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-9.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        point_annotation: Annotation = cast(Annotation, annotation_file.annotations[0])
        assert_point(point_annotation, {"x": 342.93, "y": 914.233})
        point_annotation_class = point_annotation.annotation_class
        assert_annotation_class(point_annotation_class, "Worm", "keypoint")

        tag_annotation: Annotation = cast(Annotation, annotation_file.annotations[1])
        tag_annotation_class = tag_annotation.annotation_class
        assert_annotation_class(tag_annotation_class, "r_c_or_l_side_radiograph:right", "tag")

    def test_it_imports_classification_from_checklist(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Worm",
                           "point": {"x": 342.93, "y": 914.233}
                        }
                     ],
                     "classifications": [
                        {
                           "value": "r_c_or_l_side_radiograph",
                           "answers": [{"value": "right"}, {"value": "left"}]
                        }
                     ]
                  },
                  "External ID": "demo-image-10.jpg"
               }
            ]
        """

        file_path.write_text(json)
        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-10.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        point_annotation: Annotation = cast(Annotation, annotation_file.annotations[0])
        assert_point(point_annotation, {"x": 342.93, "y": 914.233})
        point_annotation_class = point_annotation.annotation_class
        assert_annotation_class(point_annotation_class, "Worm", "keypoint")

        tag_annotation_1: Annotation = cast(Annotation, annotation_file.annotations[1])
        tag_annotation_class_1 = tag_annotation_1.annotation_class
        assert_annotation_class(tag_annotation_class_1, "r_c_or_l_side_radiograph:right", "tag")

        tag_annotation_2: Annotation = cast(Annotation, annotation_file.annotations[2])
        tag_annotation_class_2 = tag_annotation_2.annotation_class
        assert_annotation_class(tag_annotation_class_2, "r_c_or_l_side_radiograph:left", "tag")

    def test_it_imports_classification_from_free_text(file_path: Path):
        json: str = """
            [
               {
                  "Label":{
                     "objects":[
                        {
                           "title":"Shark",
                           "point": {"x": 342.93, "y": 914.233}
                        }
                     ],
                     "classifications": [
                        {
                           "value": "r_c_or_l_side_radiograph",
                           "answer": "righ side"
                        }
                     ]
                  },
                  "External ID": "demo-image-10.jpg"
               }
            ]
        """

        file_path.write_text(json)
        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        annotation_file: AnnotationFile = annotation_files.pop()
        assert annotation_file.path == file_path
        assert annotation_file.filename == "demo-image-10.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        point_annotation: Annotation = cast(Annotation, annotation_file.annotations[0])
        assert_point(point_annotation, {"x": 342.93, "y": 914.233})
        point_annotation_class = point_annotation.annotation_class
        assert_annotation_class(point_annotation_class, "Shark", "keypoint")

        tag_annotation: Annotation = cast(Annotation, annotation_file.annotations[1])
        assert_annotation_class(tag_annotation.annotation_class, "r_c_or_l_side_radiograph", "tag")
        assert_subannotations(tag_annotation.subs, [SubAnnotation(annotation_type="text", data="righ side")])


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
