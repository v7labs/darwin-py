import json

import pytest

from darwin.future.data_objects.darwinV2 import (
    BoundingBoxAnnotation,
    DarwinV2,
    EllipseAnnotation,
    PolygonAnnotation,
)


@pytest.fixture
def raw_json() -> dict:
    with open("./darwin/future/tests/data/base_annotation.json") as f:
        raw_json = json.load(f)
    return raw_json


def test_loads_base_darwin_v2(raw_json: dict) -> None:
    test = DarwinV2.model_validate(raw_json)
    assert len(test.annotations) == 3
    assert isinstance(test.annotations[0], BoundingBoxAnnotation)
    assert isinstance(test.annotations[1], EllipseAnnotation)
    assert isinstance(test.annotations[2], PolygonAnnotation)


def test_bbox_annotation(raw_json: dict) -> None:
    bounds_annotation = raw_json["annotations"][0]
    BoundingBoxAnnotation.model_validate(bounds_annotation)


def test_ellipse_annotation(raw_json: dict) -> None:
    ellipse_annotation = raw_json["annotations"][1]
    EllipseAnnotation.model_validate(ellipse_annotation)


def test_polygon_annotation(raw_json: dict) -> None:
    polygon_annotation = raw_json["annotations"][2]
    PolygonAnnotation.model_validate(polygon_annotation)


def test_polygon_bbx_validator(raw_json: dict) -> None:
    polygon_annotation = raw_json["annotations"][2]
    without_bbx = polygon_annotation.copy()
    del without_bbx["bounding_box"]
    without_bb_annotation = PolygonAnnotation.model_validate(without_bbx)
    with_bb_annotation = PolygonAnnotation.model_validate(polygon_annotation)

    assert without_bb_annotation.bounding_box is not None
    assert with_bb_annotation.bounding_box is not None
    assert without_bb_annotation == with_bb_annotation
    bounds_annotation = raw_json["annotations"][0]
    BoundingBoxAnnotation.model_validate(bounds_annotation)
