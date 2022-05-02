from typing import Any, Dict, List

from darwin.datatypes import (
    Point,
    StringData,
    StringDataSource,
    make_complex_polygon,
    make_polygon,
    make_string,
)


def describe_make_polygon():
    def it_returns_annotation_with_default_params():
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        annotation = make_polygon(class_name, points)

        assert_annoation_class(annotation, class_name, "polygon")

        path = annotation.data.get("path")
        assert path == points

    def it_returns_annotation_with_bounding_box():
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annoation_class(annotation, class_name, "polygon")

        path = annotation.data.get("path")
        assert path == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def describe_make_complex_polygon():
    def it_returns_annotation_with_default_params():
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        annotation = make_complex_polygon(class_name, points)

        assert_annoation_class(annotation, class_name, "complex_polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def it_returns_annotation_with_bounding_box():
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_complex_polygon(class_name, points, bbox)

        assert_annoation_class(annotation, class_name, "complex_polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def describe_make_string():
    def it_returns_string_annotation():
        class_name: str = "class_name"
        parameters: Dict[str, Any] = {
            "sources": [{"id": "uuid-1", "ranges": [[0, 8]]}, {"id": "uuid-2", "ranges": None}],
            "text": "the fox jumped",
        }
        annotation = make_string(class_name, parameters)

        expected_data: StringData = StringData(
            sources=[StringDataSource(id="uuid-1", ranges=[(0, 8)]), StringDataSource(id="uuid-2", ranges=None)],
            text="the fox jumped",
        )

        assert_annoation_class(annotation, class_name, "string")
        assert annotation.data == expected_data


def assert_annoation_class(annotation, name, type, internal_type=None):
    assert annotation.annotation_class.name == name
    assert annotation.annotation_class.annotation_type == type
    assert annotation.annotation_class.annotation_internal_type == internal_type
