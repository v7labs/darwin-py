import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from darwin.datatypes import (
    Point,
    make_polygon,
    parse_property_classes,
    split_paths_by_metadata,
)


class TestMakePolygon:
    def test_it_returns_annotation_with_default_params(self):
        class_name: str = "class_name"
        points: List[Point] = [[{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]]
        annotation = make_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def test_it_returns_annotation_with_bounding_box(self):
        class_name: str = "class_name"
        points: List[Point] = [[{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


class TestMakeComplexPolygon:
    def test_it_returns_annotation_with_default_params(self):
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        annotation = make_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

    def test_it_returns_annotation_with_bounding_box(self):
        class_name: str = "class_name"
        points: List[List[Point]] = [
            [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}],
            [{"x": 4, "y": 5}, {"x": 6, "y": 7}, {"x": 4, "y": 5}],
        ]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annotation_class(annotation, class_name, "polygon", "polygon")

        paths = annotation.data.get("paths")
        assert paths == points

        class_bbox = annotation.data.get("bounding_box")
        assert class_bbox == bbox


def assert_annotation_class(annotation, name, type, internal_type=None) -> None:
    assert annotation.annotation_class.name == name
    assert annotation.annotation_class.annotation_type == type
    assert annotation.annotation_class.annotation_internal_type == internal_type


@pytest.mark.parametrize(
    ("filename", "property_class_n", "properties_n"),
    (
        ("metadata.json", 1, [2]),
        ("metadata_nested_properties.json", 3, [0, 0, 1]),
        ("metadata_empty_properties.json", 3, [0, 0, 0]),
    ),
)
def test_parse_properties(filename, property_class_n, properties_n):
    metadata_path = Path(__file__).parent / f"data/{filename}"

    with open(metadata_path) as f:
        metadata = json.load(f)

    property_classes = parse_property_classes(metadata)
    assert len(property_classes) == property_class_n
    assert [
        len(property_class.properties or []) for property_class in property_classes
    ] == properties_n


@pytest.mark.parametrize(
    ("filename", "property_class_n", "properties_n", "is_properties_enabled"),
    (
        ("metadata.json", 1, [2], True),
        ("metadata_nested_properties.json", 3, [0, 0, 1], True),
        ("metadata_empty_properties.json", 0, [], False),
    ),
)
def test_split_paths_by_manifest(
    filename, property_class_n, properties_n, is_properties_enabled
):
    manifest_path = Path(__file__).parent / f"data/{filename}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmpdir_v7 = tmpdir / ".v7"
        tmpdir_v7.mkdir(exist_ok=True)
        shutil.copy(manifest_path, tmpdir_v7)

        _path, property_classes = split_paths_by_metadata(tmpdir, filename=filename)

        is_path_file = _path.is_file()
        assert is_path_file == is_properties_enabled
        assert len(property_classes or []) == property_class_n
        assert [
            len(property_class.properties or [])
            for property_class in property_classes or []
        ] == properties_n
