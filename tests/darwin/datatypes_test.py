import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List

import pytest

from darwin.datatypes import (
    Point,
    make_complex_polygon,
    make_polygon,
    parse_properties,
    split_paths_by_manifest,
)


class TestMakePolygon:
    def test_it_returns_annotation_with_default_params(self):
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        annotation = make_polygon(class_name, points)

        assert_annotation_class(annotation, class_name, "polygon")

        path = annotation.data.get("path")
        assert path == points

    def test_it_returns_annotation_with_bounding_box(self):
        class_name: str = "class_name"
        points: List[Point] = [{"x": 1, "y": 2}, {"x": 3, "y": 4}, {"x": 1, "y": 2}]
        bbox: Dict[str, float] = {"x": 1, "y": 2, "w": 2, "h": 2}
        annotation = make_polygon(class_name, points, bbox)

        assert_annotation_class(annotation, class_name, "polygon")

        path = annotation.data.get("path")
        assert path == points

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


@pytest.mark.parametrize(
    ("filename", "properties_n"),
    (
        ("manifest.json", 2),
        ("manifest_nested_properties.json", 1),
        ("manifest_empty_properties.json", 0),
    ),
)
def test_parse_properties(filename, properties_n):
    manifest_path = Path(__file__).parent / f"data/{filename}"

    with open(manifest_path) as f:
        manifest = json.load(f)

    properties = parse_properties(manifest)
    assert len(properties) == properties_n


@pytest.mark.parametrize(
    ("filename", "properties_n", "is_properties_enabled"),
    (
        ("manifest.json", 2, True),
        ("manifest_nested_properties.json", 1, True),
        ("manifest_empty_properties.json", 0, False),
    ),
)
def test_split_paths_by_manifest(filename, properties_n, is_properties_enabled):
    manifest_path = Path(__file__).parent / f"data/{filename}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_v7 = Path(tmpdir) / ".v7"
        tmpdir_v7.mkdir(exist_ok=True)
        shutil.copy(manifest_path, tmpdir_v7)

        tmpdir = Path(tmpdir)
        _path, properties = split_paths_by_manifest(tmpdir, filename=filename)

        is_path_file = _path.is_file()
        assert is_path_file == is_properties_enabled
        assert bool(properties) == is_properties_enabled
        assert len(properties or []) == properties_n
