from typing import List

import numpy as np
import pytest
from upolygon import rle_decode as upolygon_rle_decode

from darwin import datatypes as dt
from darwin.exporter.formats.mask import get_palette, get_render_mode, rle_decode


# Tests for get_palette
@pytest.mark.parametrize(
    "mode, categories, expected_output",
    [
        ("index", ["red", "green", "blue"], {"red": 0, "green": 1, "blue": 2}),
        ("grey", ["red", "green", "blue"], {"red": 0, "green": 127, "blue": 255}),
        ("rgb", ["red", "green", "blue"], {"red": 0, "green": 1, "blue": 2}),
    ],
)
def test_get_palette(mode: str, categories: List[str], expected_output: dict) -> None:
    assert get_palette(mode, categories) == expected_output


def test_get_palette_raises_value_error_when_num_categories_exceeds_maximum_for_index_mode() -> None:
    with pytest.raises(ValueError, match="maximum number of classes supported: 254."):
        get_palette("index", ["category"] * 255)


def test_get_palette_raises_value_error_when_only_one_category_provided_for_grey_mode() -> None:
    with pytest.raises(
        ValueError, match="only having the '__background__' class is not allowed. Please add more classes."
    ):
        get_palette("grey", ["__background__"])


def test_get_palette_raises_value_error_when_num_categories_exceeds_maximum_for_rgb_mode() -> None:
    with pytest.raises(ValueError, match="maximum number of classes supported: 360."):
        get_palette("rgb", ["category"] * 361)


def test_get_palette_raises_value_error_when_unknown_mode_is_provided() -> None:
    with pytest.raises(ValueError, match="Unknown mode invalid."):
        get_palette("invalid", ["red", "green", "blue"])


# Tests for get_render_mode
@pytest.fixture
def annotations() -> List[dt.Annotation]:
    return [
        dt.Annotation(dt.AnnotationClass("class_1", "raster"), data={"mask": "data", "raster_layer": "raster"}),
        dt.Annotation(dt.AnnotationClass("class_2", "polygon"), data={"polygon": "data"}),
    ]


def test_get_render_mode_returns_raster_when_given_raster_mask(annotations: List[dt.AnnotationLike]) -> None:
    assert get_render_mode([annotations[0]]) == "raster"


def test_get_render_mode_returns_polygon_when_given_polygon(annotations: List[dt.AnnotationLike]) -> None:
    assert get_render_mode([annotations[1]]) == "polygon"


def test_get_render_mode_raises_value_error_when_given_both_raster_mask_and_polygon(
    annotations: List[dt.AnnotationLike],
) -> None:
    with pytest.raises(ValueError, match="Cannot have both raster and polygon annotations in the same file"):
        get_render_mode(annotations)


def test_get_render_mode_raises_value_error_when_no_renderable_annotations_found(_) -> None:  # type: ignore
    with pytest.raises(ValueError, match="No renderable annotations found in file, found keys:"):
        get_render_mode([dt.Annotation(dt.AnnotationClass("class_3", "invalid"), data={"line": "data"})])


# Test RLE decoder
def test_rle_decoder() -> None:
    predication = [1, 2, 3, 4, 5, 6]
    expectation = [1, 1, 3, 3, 3, 3, 5, 5, 5, 5, 5, 5]

    assert rle_decode(predication) == expectation


@pytest.mark.skip("Not implemented")
def test_export() -> None:
    ...


if __name__ == "__main__":
    pytest.main()
