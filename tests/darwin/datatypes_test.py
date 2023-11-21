from typing import Dict, List

from darwin.datatypes import Point, make_complex_polygon, make_polygon


class TestMakePolygon:

    def test_it_returns_annotation_with_default_params_darwin_v2(self):
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        annotation = make_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "polygon")

        path = annotation.data.get("paths")
        assert path == [points]

    def test_it_returns_annotation_with_bounding_box_darwin_v2(self):
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bounding_box=bbox)

        assert_annotation_class(annotation, class_name, "polygon")

        path = annotation.data.get("paths")
        assert path == [points]

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


class TestMakeComplexPolygon:
    def test_it_returns_annotation_with_default_params(self):
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        annotation = make_complex_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "complex_polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def test_it_returns_annotation_with_bounding_box(self):
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_complex_polygon(class_name, points, bbox)

        assert_annotation_class(annotation, class_name, "complex_polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def assert_annotation_class(annotation, name, type, internal_type=None) -> None:
    assert annotation.annotation_class.name == name
    assert annotation.annotation_class.annotation_type == type
    assert annotation.annotation_class.annotation_internal_type == internal_type
