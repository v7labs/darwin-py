from typing import Dict, Any

import darwin.datatypes as dt
from darwin.importer.formats.coco import parse_annotation


def test_parse_annotation_single_polygon():
    """Test parsing a single polygon segmentation"""
    annotation = {
        "segmentation": [[10, 10, 20, 10, 20, 20, 10, 20]],
        "category_id": "1",
        "bbox": [10, 10, 10, 10],
        "iscrowd": 0,
    }
    category_lookup: Dict[str, Any] = {"1": {"name": "test_class"}}

    result = parse_annotation(annotation, category_lookup)

    assert len(result) == 1
    assert isinstance(result[0], dt.Annotation)
    assert result[0].annotation_class.name == "test_class"
    assert len(result[0].data["paths"]) == 1
    path = result[0].data["paths"][0]
    assert len(path) == 4
    assert path[0] == {"x": 10, "y": 10}
    assert path[2] == {"x": 20, "y": 20}


def test_parse_annotation_multiple_paths():
    """Test parsing segmentation with multiple paths in a single polygon"""
    annotation = {
        "segmentation": [
            [10, 10, 20, 10, 20, 20, 10, 20],
            [30, 30, 40, 30, 40, 40, 30, 40],
        ],
        "category_id": "1",
        "bbox": [10, 10, 30, 30],
        "iscrowd": 0,
    }
    category_lookup: Dict[str, Any] = {"1": {"name": "test_class"}}

    result = parse_annotation(annotation, category_lookup)

    assert len(result) == 1
    assert isinstance(result[0], dt.Annotation)
    assert result[0].annotation_class.name == "test_class"
    assert len(result[0].data["paths"]) == 2

    path1 = result[0].data["paths"][0]
    assert len(path1) == 4
    assert path1[0] == {"x": 10, "y": 10}
    assert path1[2] == {"x": 20, "y": 20}

    path2 = result[0].data["paths"][1]
    assert len(path2) == 4
    assert path2[0] == {"x": 30, "y": 30}
    assert path2[2] == {"x": 40, "y": 40}


def test_parse_annotation_bounding_box():
    """Test parsing a bounding box annotation"""
    annotation = {
        "segmentation": [],
        "category_id": "1",
        "bbox": [10, 20, 30, 40],
        "iscrowd": 0,
    }
    category_lookup: Dict[str, Any] = {"1": {"name": "test_class"}}

    result = parse_annotation(annotation, category_lookup)

    assert len(result) == 1
    assert isinstance(result[0], dt.Annotation)
    assert result[0].annotation_class.name == "test_class"
    assert result[0].data["x"] == 10
    assert result[0].data["y"] == 20
    assert result[0].data["w"] == 30
    assert result[0].data["h"] == 40


def test_parse_annotation_crowd():
    """Test that crowd annotations are skipped"""
    annotation = {
        "segmentation": [[10, 10, 20, 10, 20, 20, 10, 20]],
        "category_id": "1",
        "bbox": [10, 10, 10, 10],
        "iscrowd": 1,
    }
    category_lookup: Dict[str, Any] = {"1": {"name": "test_class"}}

    result = parse_annotation(annotation, category_lookup)

    assert len(result) == 0
