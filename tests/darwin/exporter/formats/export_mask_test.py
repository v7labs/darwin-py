import csv
import platform
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional
from unittest.mock import patch

import numpy as np
import pytest
from numpy.testing import assert_array_equal
from PIL import Image

try:
    from numpy.typing import NDArray
except ImportError:
    NDArray = Any  # type:ignore
from PIL import Image

from darwin import datatypes as dt
from darwin.exporter.formats.mask import (
    colours_in_rle,
    export,
    get_or_generate_colour,
    get_palette,
    get_render_mode,
    get_rgb_colours,
    render_polygons,
    render_raster,
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


def test_in_rgb_mode_spreads_colors() -> None:
    palette = get_palette("rgb", ["red", "green", "blue"])
    assert palette == {"red": 0, "green": 1, "blue": 2}

    palette = get_palette("rgb", ["red", "green", "blue", "yellow"])
    assert palette == {"red": 0, "green": 1, "blue": 2, "yellow": 3}

    palette = get_palette("rgb", ["red", "green", "blue", "yellow", "purple"])
    assert palette == {"red": 0, "green": 1, "blue": 2, "yellow": 3, "purple": 4}


def test_get_palette_raises_value_error_when_num_categories_exceeds_maximum_for_index_mode() -> (
    None
):
    with pytest.raises(ValueError, match="maximum number of classes supported: 254."):
        get_palette("index", ["category"] * 255)


def test_get_palette_raises_value_error_when_only_one_category_provided_for_grey_mode() -> (
    None
):
    with pytest.raises(
        ValueError,
        match="only having the '__background__' class is not allowed. Please add more classes.",
    ):
        get_palette("grey", ["__background__"])


def test_get_palette_raises_value_error_when_num_categories_exceeds_maximum_for_rgb_mode() -> (
    None
):
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
        dt.Annotation(
            dt.AnnotationClass("class_1", "raster_layer"),
            data={
                "dense_rle": [],
                "mask_annotation_ids_mapping": {},
                "total_pixels": 247500,
            },
        ),
        dt.Annotation(dt.AnnotationClass("class_2", "mask"), data={"sparse_rle": []}),
        dt.Annotation(dt.AnnotationClass("class_3", "polygon"), data={"path": "data"}),
        dt.Annotation(
            dt.AnnotationClass("class_4", "complex_polygon"), data={"paths": "data"}
        ),
    ]


def test_get_render_mode_returns_raster_when_given_raster_mask(
    annotations: List[dt.AnnotationLike],
) -> None:
    assert get_render_mode([annotations[0], annotations[1]]) == "raster"


def test_get_render_mode_returns_polygon_when_given_polygon(
    annotations: List[dt.AnnotationLike],
) -> None:
    assert get_render_mode([annotations[2]]) == "polygon"
    assert get_render_mode([annotations[3]]) == "polygon"


def test_get_render_mode_raises_value_error_when_given_both_raster_mask_and_polygon(
    annotations: List[dt.AnnotationLike],
) -> None:
    with pytest.raises(
        ValueError,
        match="Cannot have both raster and polygon annotations in the same file",
    ):
        get_render_mode(annotations)


def test_get_render_mode_raises_value_error_when_no_renderable_annotations_found() -> (
    None
):
    with pytest.raises(
        ValueError, match="No renderable annotations found in file, found types:"
    ):
        get_render_mode([dt.Annotation(dt.AnnotationClass("class_3", "invalid"), data={"line": "data"})])  # type: ignore


# Test colours_in_rle
@pytest.fixture
def colours() -> dt.MaskTypes.ColoursDict:
    return {"mask1": 1, "mask2": 2}


@pytest.fixture
def raster_layer() -> dt.RasterLayer:
    return dt.RasterLayer([], [], mask_annotation_ids_mapping={"uuid1": 3, "uuid2": 4})


@pytest.fixture
def mask_lookup() -> Dict[str, dt.AnnotationMask]:
    return {
        "uuid1": dt.AnnotationMask("mask3", name="mask3"),
        "uuid2": dt.AnnotationMask("mask3", name="mask4"),
    }


def test_colours_in_rle_returns_expected_dict(
    colours: dt.MaskTypes.ColoursDict,
    raster_layer: dt.RasterLayer,
    mask_lookup: Dict[str, dt.AnnotationMask],
) -> None:
    expected_dict = {"mask1": 1, "mask2": 2, "mask3": 3, "mask4": 4}
    assert colours_in_rle(colours, raster_layer, mask_lookup) == expected_dict


def test_colours_in_rle_raises_value_error_when_mask_not_in_lookup(
    colours: dt.MaskTypes.ColoursDict,
    raster_layer: dt.RasterLayer,
    mask_lookup: Dict[str, dt.AnnotationMask],
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


def test_beyond_polygon_beyond_window() -> None:
    mask = np.zeros((5, 5), dtype=np.uint8)
    colours: dt.MaskTypes.ColoursDict = {}
    categories: dt.MaskTypes.CategoryList = ["__background__"]
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "path": [
                    {"x": -1, "y": -1},
                    {"x": -1, "y": 1},
                    {"x": 1, "y": 1},
                    {"x": 1, "y": -1},
                    {"x": -1, "y": -1},
                ],
                "bounding_box": {"x": -1, "y": -1, "w": 2, "h": 2},
            },
        )
    ]
    annotation_file = dt.AnnotationFile(
        Path("testfile"),
        "testfile",
        {a.annotation_class for a in annotations},
        annotations,
    )
    height, width = 5, 5
    errors, new_mask, new_categories, new_colours = render_polygons(
        mask, colours, categories, annotations, annotation_file, height, width
    )

    expected = np.array(
        [
            [1, 1, 0, 0, 0],
            [1, 1, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ],
        dtype=np.uint8,
    )
    assert np.array_equal(new_mask, expected)
    assert not errors


def test_beyond_complex_polygon() -> None:
    mask = np.zeros((5, 5), dtype=np.uint8)
    colours: dt.MaskTypes.ColoursDict = {}
    categories: dt.MaskTypes.CategoryList = ["__background__"]
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(
            dt.AnnotationClass("cat3", "complex_polygon"),
            {
                "paths": [
                    [
                        {"x": -1, "y": -1},
                        {"x": -1, "y": 1},
                        {"x": 1, "y": 1},
                        {"x": 1, "y": -1},
                        {"x": -1, "y": -1},
                    ],
                    [
                        {"x": 3, "y": 3},
                        {"x": 3, "y": 4},
                        {"x": 4, "y": 4},
                        {"x": 4, "y": 3},
                        {"x": 3, "y": 3},
                    ],
                ],
                "bounding_box": {"x": -1, "y": -1, "w": 6, "h": 6},
            },
        ),
    ]
    annotation_file = dt.AnnotationFile(
        Path("testfile"),
        "testfile",
        {a.annotation_class for a in annotations},
        annotations,
    )
    height, width = 5, 5
    errors, new_mask, new_categories, new_colours = render_polygons(
        mask, colours, categories, annotations, annotation_file, height, width
    )

    expected = np.array(
        [
            [1, 1, 0, 0, 0],
            [1, 1, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 1, 1],
            [0, 0, 0, 1, 1],
        ],
        dtype=np.uint8,
    )
    assert np.array_equal(new_mask, expected)
    assert not errors


# Test render_polygons
def test_render_polygons() -> None:
    # Create some mock data for testing
    mask = np.zeros((100, 100), dtype=np.uint8)
    colours: dt.MaskTypes.ColoursDict = {}
    categories: dt.MaskTypes.CategoryList = ["__background__"]

    base_bb = {"x": 0, "y": 0, "w": 1, "h": 1}
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "path": [
                    {"x": 10, "y": 10},
                    {"x": 20, "y": 10},
                    {"x": 20, "y": 20},
                    {"x": 10, "y": 20},
                ],
                "bounding_box": base_bb,
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat2", "polygon"),
            {
                "path": [
                    {"x": 30, "y": 30},
                    {"x": 40, "y": 30},
                    {"x": 40, "y": 40},
                    {"x": 30, "y": 40},
                ],
                "bounding_box": base_bb,
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "path": [
                    {"x": 50, "y": 50},
                    {"x": 60, "y": 50},
                    {"x": 60, "y": 60},
                    {"x": 50, "y": 60},
                ],
                "bounding_box": base_bb,
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "path": [{"x": 10, "y": 80}, {"x": 20, "y": 80}, {"x": 20, "y": 60}],
                "bounding_box": base_bb,
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat3", "complex_polygon"),
            {
                "paths": [
                    [
                        {"x": 70, "y": 70},
                        {"x": 80, "y": 70},
                        {"x": 80, "y": 80},
                        {"x": 70, "y": 80},
                    ],
                    [{"x": 75, "y": 75}, {"x": 75, "y": 78}, {"x": 78, "y": 78}],
                ],
                "bounding_box": base_bb,
            },
        ),
    ]
    annotation_file = dt.AnnotationFile(
        Path("testfile"),
        "testfile",
        {a.annotation_class for a in annotations},
        annotations,
    )
    height = 100
    width = 100

    # Call the function with the mock data
    errors, new_mask, new_categories, new_colours = render_polygons(
        mask, colours, categories, annotations, annotation_file, height, width
    )

    assert not errors

    # Check that the mask was modified in place
    assert_array_equal(mask, new_mask)  # type: ignore

    # Check that the categories and colours were updated correctly
    assert new_categories == ["__background__", "cat1", "cat2", "cat3"]
    assert new_colours == {"cat1": 1, "cat2": 2, "cat3": 3}

    # Check that the polygons were drawn correctly

    this_file_dir = Path(__file__).parent
    expected_data_path = (this_file_dir / ".." / ".." / "data").resolve()
    expected_mask: NDArray = np.array(np.fromfile(expected_data_path / "expected_mask.bin", dtype=np.uint8)).reshape(  # type: ignore
        (100, 100)
    )

    assert_array_equal(new_mask, expected_mask)  # type: ignore


# Test render_raster
def test_render_raster() -> None:
    rle_code: List[int] = [
        int(c)
        for c in "1212213111132231132123132221223231113221112111233221121231311132313311221123131313131331113221311322333312233113311333132133212131122313313223111221323331221233312221221233133232232211321321311321133113123232322233222331223321121121113133313113232323122131123322122233311131213132123232322221113131331212212322133121231221213113231322121332222121232133222321311213312332321321212321222121113223321113311333313222232213123121221132332113321132133121221212131123113233313112322332112312113112321222331332121311132312221331312222211113232131112123331121311213113321121223323323232211323113333333321323332312332232332223332123213211332131112121131112233321131112121233131331133223211131333223123121322221332333311213331231122133311131211132231233111322123331223311231323121233233231222331331211322123213112211211231222323113331211113311331332221331131311112213322313322233213122133112313311322133223123221211113333222311222311133331312113322321312312122321133111133233313321221323231331223131321213332123331232123323313332232211312211133221113122322332131212112312121211113122221222131112333322323222312232311312321132212113311111131111113123133323333331212133312312122331212323223311121332232133212333212213132121321232211212233333313311332321231111333122133321211131312221113331112112121122212122322132213113123222231212331312233312113213233233312323211133132131133122311122321132233112313212312122332331312131213213223233222213112312111221131111232223123322133322111221323233333331313221222233322233221213131212322121112323312312321111333132323113331132312232231322232332223223211331322222231122211111311323221331111112123231131212131231112322322321333112331223111311311113123233223123311321322313231222311112113131133111233212121322212131221231222331233222212333312222223313232111111121113132221223332121222311121312322313221211131323111112233231131123111131122321312212112313221131221321221212331333232323132131131211223322221312331122123131332322322321212232232112321112313313322231122222331222323221113211121121322211223212133111332111112133213213323112112232223222333223312312123211122223333332321112322311132311113133233332132322332113121223323313232331211121333111123132321322331132131211331322222212113213321322111233311212131121322231132313221112122113213313312121331322131131112113311112232212222232112222213213111231231311111333233113122321113133323113231112121211113231232313233233333221333333311221131223111213122213112332311331211211113231212132322133211212121211312333331332322211213331311312223233212223312112121311323232122333221232213323122322122313332121212313221332233211222113222232223212233211313311132313212213312112111121332231231131232321313122332311312232321121233332131122131113212331223211322333232221321311133332231312122311321322222132232323123311133133122332313122231131111323133331233221121111111331122323111133331112323122123113213122332122222113113321132222312223131323123323222131323321231211312222213131333123132333133321323131231212311133222232133321333111212231331133131312333231333213321321212311123131232211123212123231122122321111132323321113131331233321323122232313311332111112321211232132112313132322111313121112231312333131212221322122123331322123212121333311111332312222132321333133323211113321113111333232333312231212123232322223122332233133222211112113121322113231212323322132331111133231131312223212123222121121323212123232221331113112321322212323323331231311321233331331331221322323231221313111132121331123221131211112211212323221322113323112333213323232333313321232123332231232223323331133222232122222112112123323212131133121331233311222121112231313111332322112122232133122111323123133123112233323121113133223132223333333332332211331321111212323212121113232313322123131321312132113321323233311123222121333232322321121332322133323123332322112111131233212111131122113332133222113221122222133112333123121322323331232113133322312222233113223312123112332211132322213313231313133111321113321131222122331311331312131322111323111113123322112122312223333113133112322231323123213231231312323311331112111122212312312131332333223221112222311232131333211232323233112221123111132232332111321313323231312212113232331212211232121213233221211231312132131312231222122131213233321211132312311321323211323223311323223311313313131311121312122322121211123113231123212133231322122321232221131212311323221323233332122133213111311122133323312122123112332332313132322313233312233322221111133212112231333222221233312311223211311331213121133231212233211132122331332223222322223122233232112211233123312222231131232232113113221212333133131311332313321321331122232221322123233323211232323212312211312132321321123123333131132332331133131122132332112333123323232211122232213333112232223312332112222223313132122212131233322131113132322312233113232311231323211332231233223312233221232323332311133322322112133122133211312233321123232212332132222213333233212213313133333223232333121322212321213321333212321213223323133113213131222232233212322331232331231223222331112111322312222113133112321231331213121211122332232322133321123133111312132133122132111322312232332213322233121121331312221121213231222131223231113311321331123333122111211332231312313321213221331223123323112112222232132132123212112221212122313311322122232223112331233111131221321121132333221323323123123332133311223123121231222322231121122211121111132121222322311323231212322211211133111221313122133332132323321211112121331113322232231323133323121221111111323233213232212312331133123323133132331112213122111313222312333332333111212123311323231132222332333323233132133213223131133332221223212112323121221212331131322223232123132323232131111312233221122112122213112232321312132112323221322111332232123132312231111232132221121221212222323311232223123111123233322211121111221223222223331213132123321212222212113212121132233312332132131311231311232233322323312221211211122121323131121323221313122232131121313312123321212311213131133223332131122213331311333221312323232223223331113331233312112112111111233321231133121122123132222312121211322333213233313222123123113332331131223231332232123312232132222233223312233322331231232112323321312132211133311321313132221312113212333322132313321132313111213122313132111321222333333322211322122312233111323123121333321222311332223311232212222132312231313131132223133113312312311322321311113131233333213321312223322213132213222113221221221213231312321313223323233122311323121212113311321221221313131113211222332213213133123311213323122223313321313132313322211123123221223312113311211112123223313321322323233212121213121113132323113233332233211132112121212221313332311332123211231211321331233131133311221213311121323311111313112213232312312212311112333113331333121123123313111323331121213323323223111221331211211131111331233233122223321112123321231212321232221122122333313223211222333113212111221121113221221111133323111323121211311132113121221233322312232221333333212111131233321122312213311233332321123131321113221131323223323312113133231311132221113112132132113123232132321112232213222221213122123133212321222131132131123133133122232323122233213123311131121213221311222311332211113312211221212131112113312132233231222121213132323121212232321112333221333311231311223322321111232232112323233233322213213123111111122313212232113331233111311311131122212311131121133122112222331212332321312133333131313313223231123232213322131211233212112332331123132232132132222211123122111213232332223212213223112111332221121113211111113111311133322213132223312232113321132221232221123131311231313113122111211122122322333231121113131323113232122113232111121213222311131231112122113333123321322223233323212322331233332112132333111211112212322313312132211231122222113322133323132311212332231211312333123121132122233212312123311111311331222131123323111122321112213212111322121131111123312332122211213133211312211132223212323133121212323113322131123212322233231323122113322213222332332133212313313312211213232131222311132321332232223212112222212113212211131223323332212322323222233332311322132113322231333231333121122312122313322113221212221231333133112133222112113111332113331122312123331332131113111213333122331111332122313123231331221223131131233132113122312212212321121222121123113333131123321232313113212313111322322133221333223221333213212333312233212231113331111133212312311111122232322233231332313223113331233112223123313123221113211213331331221121222323111213322231232133333233332132223133121323213122232312333323221322211121331122312123223122132122232233322322231112223333113213113112322213212132112122212121233121212123332321312322211222222321122231222312312231213213123132232333213113213323313311123133322312231231123232213133222221233212111111221313332113131333223223222132132333213221131132131323132233323221331132221111222211322321223213132221311323332132223223212323313221222232211311222321223321333331323221232133121321213121111113212112211331132122321333322232211321313113311221133312322212211111222133233322332123111113212112233133111331121322223223231212133223333332211231232331331212132133323222133133131322123323232221122123133331113222132133333211131133112211333323112121233311323112222331311212113111232113221213122333133213231333111213223222133113321112122322211131322212112211323333323332213331112132121132123231112223131222313331331313232232322213311113223331122232121311221121231131323321211133212332112121332223211321311312232111123322113121323333212222213111333311133322221311112333313222222231311331223113323212312211211323223113211223323113113131331213132313323231322313123111221221131123121221211112133112131332331211113313322322321322132111312331311131132313123312231111333133211122233212232311223131332213133223331232113122112122221231232221112332221223312223322332221223211222223332112311312313331122221211211132322231312331311222322132331233133113323133322331322221223331332211233222332113313233332123121112211121131131321222233223312233312122213133232123321232333232233213331123132313113221133322233213123113131212321213113322323133231321211323311123232312132311212322122233121"
    ]
    mask = np.zeros((100, 100), dtype=np.uint8)
    colours: dt.MaskTypes.ColoursDict = {}
    categories: dt.MaskTypes.CategoryList = []
    annotations: List[dt.AnnotationLike] = [
        dt.Annotation(
            dt.AnnotationClass("mask1", "mask"),
            {"sparse_rle": None},
            subs=[],
            id="mask1",
            slot_names=["slot1"],
        ),
        dt.Annotation(
            dt.AnnotationClass("mask2", "mask"),
            {"sparse_rle": None},
            subs=[],
            id="mask2",
            slot_names=["slot1"],
        ),
        dt.Annotation(
            dt.AnnotationClass("mask3", "mask"),
            {"sparse_rle": None},
            subs=[],
            id="mask3",
            slot_names=["slot1"],
        ),
        dt.Annotation(
            dt.AnnotationClass("__raster_layer__", "raster_layer"),
            {
                "dense_rle": "my_rle_data",
                "decoded": rle_code,
                "mask_annotation_ids_mapping": {"mask1": 0, "mask2": 1, "mask3": 2},
                "total_pixels": 10000,
            },
            slot_names=["slot1"],
            id="raster",
        ),
    ]
    annotation_file = dt.AnnotationFile(
        Path("path"),
        annotations=annotations,
        annotation_classes={c.annotation_class for c in annotations},
        filename="test.txt",
    )

    with patch("darwin.exporter.formats.mask.rle_decode") as mock_rle_decode, patch(
        "darwin.exporter.formats.mask.colours_in_rle"
    ) as mock_colours_in_rle:
        mock_rle_decode.return_value = rle_code
        mock_colours_in_rle.return_value = {"mask1": 1, "mask2": 2, "mask3": 3}

        errors, result_mask, result_categories, result_colours = render_raster(
            mask, colours, categories, annotations, annotation_file, 100, 100
        )

        assert not errors

        assert result_mask.shape == (100, 100)
        assert not np.all(result_mask == 0)

        expected_ones, expected_twos, expected_threes = (
            len([x for x in rle_code if x == 1]),
            len([x for x in rle_code if x == 2]),
            len([x for x in rle_code if x == 3]),
        )
        assert np.sum(result_mask == 1) == expected_ones
        assert np.sum(result_mask == 2) == expected_twos
        assert np.sum(result_mask == 3) == expected_threes
        # If we get this far, mask is either the same, or has coincidentally similar counts

        assert_array_equal(result_mask, np.array(rle_code, dtype=np.uint8).reshape((100, 100)))  # type: ignore

        assert result_categories == ["mask1", "mask2", "mask3"]
        assert result_colours == {"mask1": 1, "mask2": 2, "mask3": 3}


# Test the export function
RED = [255, 0, 0]
GREEN = [0, 255, 0]
BLUE = [0, 0, 255]
BLACK = [0, 0, 0]


def colours_for_test() -> dt.MaskTypes.RgbColors:
    return [*BLACK, *RED, *GREEN, *BLUE]


def colour_list_for_test() -> dt.MaskTypes.ColoursDict:
    return {"mask1": 0, "mask2": 1, "mask3": 2}


data_path = (Path(__file__).parent / ".." / ".." / "data").resolve()


def polygon_shape() -> NDArray:
    return np.fromfile(data_path / "expected_mask.bin", dtype=np.uint8).reshape((100, 100))  # type: ignore


def raster_shape() -> NDArray:
    return np.array(np.repeat([0, 1, 2, 3], 25), dtype=np.uint8).reshape(10, 10)


@pytest.mark.parametrize(
    "colour_mode, render_mode, renderer_output, expected_mask_file, expected_csv_file",
    [
        (
            "rgb",
            "raster",
            (
                [],
                raster_shape(),
                ["class1", "class2", "class3"],
                {"class1": 1, "class2": 2, "class3": 3},
            ),
            data_path / "expected_image_rgb.png",
            data_path / "expected_classes_rgb.csv",
        ),
        (
            "grey",
            "raster",
            (
                [],
                raster_shape(),
                ["class1", "class2", "class3"],
                {"class1": 1, "class2": 2, "class3": 3},
            ),
            data_path / "expected_image_grey.png",
            data_path / "expected_classes_grey.csv",
        ),
        (
            "index",
            "raster",
            (
                [],
                raster_shape(),
                ["class1", "class2", "class3"],
                {"class1": 1, "class2": 2, "class3": 3},
            ),
            data_path / "expected_image_index.png",
            data_path / "expected_classes_index.csv",
        ),
        (
            "rgb",
            "polygon",
            (
                [],
                polygon_shape(),
                ["class1", "class2", "class3"],
                {"class1": 1, "class2": 2, "class3": 3},
            ),
            data_path / "expected_polygons_image_rgb.png",
            data_path / "expected_classes_rgb.csv",
        ),
        (
            "grey",
            "polygon",
            (
                [],
                polygon_shape(),
                ["class1", "class2", "class3"],
                {"class1": 1, "class2": 2, "class3": 3},
            ),
            data_path / "expected_polygons_image_grey.png",
            data_path / "expected_classes_grey.csv",
        ),
        (
            "index",
            "polygon",
            (
                [],
                polygon_shape(),
                ["class1", "class2", "class3"],
                {"class1": 1, "class2": 2, "class3": 3},
            ),
            data_path / "expected_polygons_image_index.png",
            data_path / "expected_classes_index.csv",
        ),
    ],
)
def test_export(
    colour_mode: dt.MaskTypes.Mode,
    render_mode: dt.MaskTypes.TypeOfRender,
    renderer_output: dt.MaskTypes.RendererReturn,
    expected_mask_file: Optional[Path],
    expected_csv_file: Optional[Path],
) -> None:
    with TemporaryDirectory() as output_dir, patch(
        "darwin.exporter.formats.mask.get_render_mode"
    ) as mock_get_render_mode, patch(
        "darwin.exporter.formats.mask.render_raster"
    ) as mock_render_raster, patch(
        "darwin.exporter.formats.mask.render_polygons"
    ) as mock_render_polygons, patch(
        "darwin.exporter.formats.mask.get_palette"
    ) as mock_get_palette, patch(
        "darwin.exporter.formats.mask.get_rgb_colours"
    ) as mock_get_rgb_colours:
        height, width = renderer_output[1].shape

        annotation_files = [
            dt.AnnotationFile(
                Path("test"),
                "test",
                annotation_classes=set(),
                annotations=[],
                image_height=height,
                image_width=width,
            )
        ]

        mock_get_render_mode.return_value = render_mode

        if colour_mode == "rgb":
            mock_get_rgb_colours.return_value = (
                colours_for_test(),
                {
                    "__background__": [0, 0, 0],
                    "class1": [255, 0, 0],
                    "class2": [0, 255, 0],
                    "class3": [0, 0, 255],
                },
            )

        if colour_mode == "rgb" or colour_mode == "index":
            mock_get_palette.return_value = {
                "__background__": 0,
                "class1": 1,
                "class2": 2,
                "class3": 3,
            }
        else:
            mock_get_palette.return_value = {
                "__background__": 0,
                "class1": 85,
                "class2": 170,
                "class3": 255,
            }

        if render_mode == "raster":
            # Raster run
            mock_render_raster.return_value = renderer_output
        else:
            mock_get_render_mode.return_value = "polygon"
            mock_render_polygons.return_value = renderer_output

        export(annotation_files, Path(output_dir), colour_mode)

        """
        Assertions based on function calls
        """

        # The things always called
        assert mock_get_render_mode.called
        assert mock_get_palette.called

        if render_mode == "raster":
            # The things called only for raster
            assert mock_render_raster.called
            assert not mock_render_polygons.called

        else:
            # The things called only for polygon
            assert mock_render_polygons.called
            assert not mock_render_raster.called

        """
        Assertions based on output files
        """
        # CSV File
        if expected_csv_file and not platform.system() == "Windows":
            test_csv_path = Path(output_dir) / "class_mapping.csv"
            assert expected_csv_file.exists()
            assert test_csv_path.exists()

            with expected_csv_file.open("r") as expected_csv, test_csv_path.open(
                "r"
            ) as test_output_csv:
                assert expected_csv.read() == test_output_csv.read()

        # PNG File
        if expected_mask_file and not platform.system() == "Windows":
            test_png_path = Path(output_dir) / "masks" / "test.png"
            assert expected_mask_file.exists()
            assert test_png_path.exists()

            expected = Image.open(expected_mask_file).convert("RGB")
            test_output = Image.open(test_png_path).convert("RGB")

            assert expected.width == test_output.width
            assert expected.height == test_output.height
            assert expected.mode == test_output.mode

            for x in range(expected.width):
                for y in range(expected.height):
                    assert expected.getpixel((x, y)) == test_output.getpixel(
                        (x, y)
                    ), f"Pixel {x},{y} is different"


def test_class_mappings_preserved_on_large_export(tmpdir) -> None:
    """
    Integration Test to ensure that class mappings are preserved on large exports with multiple files,
    it does this by creating annotations of different but fixed sizes and ensuring that the class mappings
    are the same for each file. This is to ensure that the class mappings are not being reset between files
    or annotation classes are being re-indexed and assigned a different colour.
    """

    height, width = 10, 10
    annotations = [
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "path": [
                    {"x": 0, "y": 0},
                    {"x": 1, "y": 0},
                    {"x": 1, "y": 1},
                    {"x": 0, "y": 1},
                    {"x": 0, "y": 1},
                ],
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat2", "polygon"),
            {
                "path": [
                    {"x": 2, "y": 2},
                    {"x": 4, "y": 2},
                    {"x": 4, "y": 4},
                    {"x": 2, "y": 4},
                    {"x": 2, "y": 2},
                ],
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat3", "polygon"),
            {
                "path": [
                    {"x": 5, "y": 5},
                    {"x": 8, "y": 5},
                    {"x": 8, "y": 8},
                    {"x": 5, "y": 8},
                    {"x": 5, "y": 5},
                ],
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat1", "polygon"),
            {
                "path": [
                    {"x": 4, "y": 0},
                    {"x": 5, "y": 0},
                    {"x": 5, "y": 1},
                    {"x": 4, "y": 1},
                    {"x": 4, "y": 0},
                ],
            },
        ),
        dt.Annotation(
            dt.AnnotationClass("cat4", "complex_polygon"),
            {
                "paths": [
                    [
                        {"x": 0, "y": 3},
                        {"x": 1, "y": 3},
                        {"x": 1, "y": 5},
                        {"x": 0, "y": 5},
                        {"x": 0, "y": 3},
                    ],
                    [
                        {"x": 0, "y": 7},
                        {"x": 1, "y": 7},
                        {"x": 1, "y": 8},
                        {"x": 0, "y": 8},
                        {"x": 0, "y": 7},
                    ],
                ]
            },
        ),
    ]
    # Pixel sizes of polygons, for used in asserting the correct colour is mapped to the correct class
    sizes = {"cat1": 8, "cat2": 9, "cat3": 16, "cat4": 10}
    sizes["__background__"] = height * width - sum(list(sizes.values()))
    annotation_files = [
        dt.AnnotationFile(
            Path(f"test{x}"),
            f"test{x}",
            annotation_classes=set(),
            annotations=annotations,
            image_height=height,
            image_width=width,
        )
        for x in range(100)
    ]
    output_directory = tmpdir.mkdir("output")
    export(annotation_files, Path(output_directory), "rgb")
    class_mapping = {}
    with open(Path(output_directory) / "class_mapping.csv", "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f, delimiter=",")
        next(csv_reader, None)
        for row in csv_reader:
            if not row:
                continue
            rgb = row[1].split(" ")
            class_mapping[row[0]] = [int(rgb[0]), int(rgb[1]), int(rgb[2])]

        # maps the (r,g,b) tuple to the class name
        inverse_mapping = {tuple(v): k for k, v in class_mapping.items()}
    assert len(class_mapping) == len(sizes)
    for item in annotation_files:
        assert Path(output_directory) / "masks" / f"{item.filename}.png"
        filepath = Path(output_directory) / "masks" / f"{item.filename}.png"
        image = Image.open(filepath)

        # Check that the image contains the correct number of pixels for each class by mapping
        # the pixel colour to the class and checking the number of pixels of that colour
        np_image = np.array(image)
        flat_image = np_image.reshape(-1, np_image.shape[-1])
        colours, counts = np.unique(flat_image, axis=0, return_counts=True)  # type: ignore
        assert len(colours) == len(counts)
        assert len(colours) == len(sizes)

        for index, colour in enumerate(colours):
            # regardless of particular colours assigned, the pixel count should be the same for that (r,g,b) tuple
            assert tuple(colour) in inverse_mapping
            assert counts[index] == sizes[inverse_mapping[tuple(colour)]]


if __name__ == "__main__":
    pytest.main()
