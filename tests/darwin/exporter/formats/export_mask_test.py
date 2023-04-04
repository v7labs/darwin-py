from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
from PIL import Image

from darwin import datatypes as dt
from darwin.exporter.formats.mask import (
    colours_in_rle,
    get_or_generate_colour,
    get_palette,
    get_render_mode,
    get_rgb_colours,
    render_polygons,
    rle_decode,
)


# Tests for get_palette
def test_in_grey_mode_spreads_colors_evenly() -> None:
    palette = get_palette("grey", ["red", "green", "blue"])
    assert palette == {"red": 0, "green": 127, "blue": 255}

    palette = get_palette("grey", ["red", "green", "blue", "yellow"])
    assert palette == {"red": 0, "green": 85, "blue": 170, "yellow": 255}

    palette = get_palette("grey", ["red", "green", "blue", "yellow", "purple"])
    assert palette == {"red": 0, "green": 63, "blue": 127, "yellow": 191, "purple": 255}


def test_in_index_mode_doesnt_spread_colors() -> None:
    palette = get_palette("index", ["red", "green", "blue"])
    assert palette == {"red": 0, "green": 1, "blue": 2}

    palette = get_palette("index", ["red", "green", "blue", "yellow"])
    assert palette == {"red": 0, "green": 1, "blue": 2, "yellow": 3}

    palette = get_palette("index", ["red", "green", "blue", "yellow", "purple"])
    assert palette == {"red": 0, "green": 1, "blue": 2, "yellow": 3, "purple": 4}


def test_in_rgb_mode_spreads_colors_evenly() -> None:
    palette = get_palette("rgb", ["red", "green", "blue"])
    assert palette == {"red": 0, "green": 1, "blue": 2}

    palette = get_palette("rgb", ["red", "green", "blue", "yellow"])
    assert palette == {"red": 0, "green": 1, "blue": 2, "yellow": 3}

    palette = get_palette("rgb", ["red", "green", "blue", "yellow", "purple"])
    assert palette == {"red": 0, "green": 1, "blue": 2, "yellow": 3, "purple": 4}


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
        get_palette("invalid", ["red", "green", "blue"])  # type: ignore


# Tests for get_rgb_colours
@pytest.mark.parametrize(
    "categories, expected_rgb_colours, expected_palette_rgb",
    [
        (
            ["Category1", "Category2", "Category3"],
            [0, 0, 0, 255, 50, 50, 50, 255, 50],
            {
                "Category1": [0, 0, 0],
                "Category2": [255, 50, 50],
                "Category3": [50, 255, 50],
            },
        ),
        (
            ["Category1", "Category2", "Category3", "Category4"],
            [0, 0, 0, 255, 50, 50, 153, 255, 50, 50, 255, 255],
            {
                "Category1": [0, 0, 0],
                "Category2": [255, 50, 50],
                "Category3": [153, 255, 50],
                "Category4": [50, 255, 255],
            },
        ),
        (
            ["Category1", "Category2", "Category3", "Category4", "Category5"],
            [0, 0, 0, 255, 50, 50, 214, 255, 50, 50, 255, 132, 50, 132, 255],
            {
                "Category1": [0, 0, 0],
                "Category2": [255, 50, 50],
                "Category3": [214, 255, 50],
                "Category4": [50, 255, 132],
                "Category5": [50, 132, 255],
            },
        ),
    ],
)
def test_get_rgb_colours(
    categories: dt.MaskTypes.CategoryList,
    expected_rgb_colours: dt.MaskTypes.RgbColors,
    expected_palette_rgb: dt.MaskTypes.RgbPalette,
) -> None:
    rgb_colours, palette_rgb = get_rgb_colours(categories)

    assert len(rgb_colours) == len(expected_rgb_colours)
    assert len(palette_rgb) == len(expected_palette_rgb)

    for i in range(len(expected_rgb_colours)):
        assert rgb_colours[i] == expected_rgb_colours[i]

    for category in categories:
        assert palette_rgb[category] == expected_palette_rgb[category]


# Test for get_or_generate_colour
def test_get_or_generate_colour() -> None:
    colours = {"cat1": 1, "cat2": 2}

    # Test that it returns an existing color
    assert get_or_generate_colour("cat1", colours) == 1

    # Test that it generates a new color for a new category
    assert get_or_generate_colour("cat3", colours) == 3

    # Test that the colors dictionary is updated with the new category
    assert colours == {"cat1": 1, "cat2": 2, "cat3": 3}


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


def test_get_render_mode_raises_value_error_when_no_renderable_annotations_found() -> None:  # type: ignore
    with pytest.raises(ValueError, match="No renderable annotations found in file, found keys:"):
        get_render_mode([dt.Annotation(dt.AnnotationClass("class_3", "invalid"), data={"line": "data"})])


# Test colours_in_rle
@pytest.fixture
def colours() -> dt.MaskTypes.ColoursDict:
    return {"mask1": 1, "mask2": 2}


@pytest.fixture
def raster_layer() -> dt.RasterLayer:
    return dt.RasterLayer([], [], mask_mappings={"uuid1": 3, "uuid2": 4})


@pytest.fixture
def mask_lookup() -> Dict[str, dt.AnnotationMask]:
    return {"uuid1": dt.AnnotationMask("mask3", name="mask3"), "uuid2": dt.AnnotationMask("mask3", name="mask4")}


def test_colours_in_rle_returns_expected_dict(
    colours: dt.MaskTypes.ColoursDict, raster_layer: dt.RasterLayer, mask_lookup: Dict[str, dt.AnnotationMask]
) -> None:
    expected_dict = {"mask1": 1, "mask2": 2, "mask3": 3, "mask4": 4}
    assert colours_in_rle(colours, raster_layer, mask_lookup) == expected_dict


def test_colours_in_rle_raises_value_error_when_mask_not_in_lookup(
    colours: dt.MaskTypes.ColoursDict, raster_layer: dt.RasterLayer, mask_lookup: Dict[str, dt.AnnotationMask]
) -> None:
    with pytest.raises(ValueError):
        colours_in_rle(
            colours,
            raster_layer,
            {
                "uuid9": dt.AnnotationMask("9", name="mask9"),
                "uuid10": dt.AnnotationMask("10", name="mask10"),
                "uuid11": dt.AnnotationMask("11", name="mask11"),
            },
        )


# Test RLE decoder
def test_rle_decoder() -> None:
    predication = [1, 2, 3, 4, 5, 6]
    expectation = [1, 1, 3, 3, 3, 3, 5, 5, 5, 5, 5, 5]

    assert rle_decode(predication) == expectation

    odd_number_of_integers = [1, 2, 3, 4, 5, 6, 7]
    with pytest.raises(ValueError):
        rle_decode(odd_number_of_integers)


# Test render_polygons
def test_render_polygons() -> None:
    # Create some mock data for testing
    mask = Image.new("RGB", (100, 100), color=(0, 0, 0))
    colours: dt.MaskTypes.ColoursDict = {}
    categories: dt.MaskTypes.CategoryList = []
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(dt.AnnotationClass("cat1", "polygon"), {"path": [(10, 10), (20, 10), (20, 20), (10, 20)]}),
        dt.Annotation(dt.AnnotationClass("cat2", "polygon"), {"path": [(30, 30), (40, 30), (40, 40), (30, 40)]}),
        dt.Annotation(dt.AnnotationClass("cat1", "polygon"), {"path": [(50, 50), (60, 50), (60, 60), (50, 60)]}),
        dt.Annotation(
            dt.AnnotationClass("cat3", "complex_polygon"),
            {"paths": [[(70, 70), (80, 70), (80, 80), (70, 80)], [(75, 75), (75, 78), (78, 78)]]},
        ),
    ]
    annotation_file = dt.AnnotationFile(
        Path("testfile"),
        "testfile",
        set([a.annotation_class for a in annotations]),
        annotations,
    )
    height = 100
    width = 100

    # Call the function with the mock data
    errors, new_mask, new_categories, new_colours = render_polygons(
        mask, colours, categories, annotations, annotation_file, height, width
    )

    # Check that the mask was modified in place
    assert mask == new_mask

    # Check that the categories and colours were updated correctly
    assert new_categories == ["cat1", "cat2", "cat3"]
    assert new_colours == {"cat1": 1, "cat2": 2, "cat3": 3}

    # Check that the polygons were drawn correctly
    assert new_mask.getpixel((15, 15)) == (255, 0, 0)  # cat1
    assert new_mask.getpixel((35, 35)) == (0, 255, 0)  # cat2
    assert new_mask.getpixel((55, 55)) == (255, 0, 0)  # cat1
    assert new_mask.getpixel((75, 75)) == (0, 0, 255)  # cat3
    assert new_mask.getpixel((77, 77)) == (0, 0, 255)  # cat3


@pytest.mark.skip("Not implemented")
def test_export() -> None:
    ...


if __name__ == "__main__":
    pytest.main()
