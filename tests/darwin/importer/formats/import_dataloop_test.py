from json import loads as json_loads
from math import isclose as math_isclose
from os.path import dirname, join, realpath
from pathlib import Path
from typing import Dict, Tuple, Union
from unittest import TestCase
from unittest.mock import MagicMock, patch

from darwin.datatypes import Annotation
from darwin.exceptions import UnsupportedImportAnnotationType
from darwin.importer.formats.dataloop import (
    _parse_annotation,
    _remove_leading_slash,
    parse_path,
)


class DataLoopTestCase(TestCase):
    def setUp(self) -> None:
        _fd = open(realpath(join(dirname(__file__), "..", "..", "data", "dataloop.example.json")))
        self.DATALOOP_MOCK_DATA = _fd.read()
        _fd.close()

    def assertApproximatelyEqualNumber(self, a: Union[int, float], b: Union[int, float], places: int = 8):
        math_isclose(a, b, rel_tol=10**-places)

    DARWIN_PARSED_DATA = {
        "filename": "test.jpg",
        "annotations": [
            {"class": "class_1"},
            {"class": "class_2"},
            {"class": "class_3"},
        ],
    }


class TestParsePath(DataLoopTestCase):
    def tearDown(self):
        patch.stopall()

    @patch(
        "darwin.importer.formats.dataloop._remove_leading_slash",
    )
    def test_returns_none_if_file_extension_is_not_json(self, mock_remove_leading_slash):
        self.assertIsNone(parse_path(Path("foo.bar")))

    @patch(
        "darwin.importer.formats.dataloop._remove_leading_slash",
    )
    @patch("darwin.importer.formats.dataloop.json.load")
    @patch("darwin.importer.formats.dataloop.Path.open")
    @patch("darwin.importer.formats.dataloop._parse_annotation")
    def test_opens_annotations_file_and_parses(
        self,
        _parse_annotation_mock: MagicMock,
        path_open_mock: MagicMock,
        json_load_mock: MagicMock,
        mock_remove_leading_slash: MagicMock,
    ):
        json_load_mock.return_value = self.DARWIN_PARSED_DATA
        test_path = "foo.json"

        parse_path(Path(test_path))

        self.assertEqual(_parse_annotation_mock.call_count, 3)
        path_open_mock.assert_called_once()
        json_load_mock.assert_called_once()
        mock_remove_leading_slash.assert_called_once()


class TestRemoveLeadingSlash(DataLoopTestCase):
    def tearDown(self) -> None:
        patch.stopall()

    def test_removes_slash_if_present(self):
        self.assertEqual(_remove_leading_slash("/foo"), "foo")

    def test_does_not_remove_slash_if_not_present(self):
        self.assertEqual(_remove_leading_slash("foo"), "foo")


class TestParseAnnotation(DataLoopTestCase):
    def setUp(self):
        super().setUp()
        self.parsed_json = json_loads(self.DATALOOP_MOCK_DATA)

    def tearDown(self) -> None:
        patch.stopall()

    def test_handles_box_type(self):
        from darwin.importer.formats.dataloop import _parse_annotation as pa

        with patch("darwin.importer.formats.dataloop.dt.make_bounding_box") as make_bounding_box_mock:
            make_bounding_box_mock.return_value = Annotation("class_1", 0, 0, 0, 0)
            pa(self.parsed_json["annotations"][0])  # 0 is a box type

            make_bounding_box_mock.assert_called_with("box_class", 288.81, 845.49, 1932.5100000000002, 2682.75)

    def test_handles_class_type(self):
        annotation = _parse_annotation(self.parsed_json["annotations"][1])  # 1 is a class type
        self.assertEqual(annotation, None)

    def test_handles_segment_type(self):
        from darwin.importer.formats.dataloop import _parse_annotation as pa

        with patch("darwin.importer.formats.dataloop.dt.make_polygon") as make_polygon_mock:
            pa(self.parsed_json["annotations"][2])  # 2 is a segment type

            if "kwargs" in make_polygon_mock.call_args:

                def make_tuple_entry(point: Dict[str, float]) -> Tuple[float, float]:
                    return (point["x"], point["y"])

                point_path = [make_tuple_entry(p) for p in make_polygon_mock.call_args.kwargs["point_path"]]
                expectation_points = [
                    (856.73076923, 1077.88461538),
                    (575, 657.69230769),
                    (989.42307692, 409.61538462),
                    (974.03846154, 640.38461538),
                    (1033.65384615, 915.38461538),
                    (1106.73076923, 1053.84615385),
                    (1204.80769231, 1079.80769231),
                ]

                [
                    self.assertApproximatelyEqualNumber(a[0], b[0]) and self.assertApproximatelyEqualNumber(a[1], b[1])
                    for a, b in zip(point_path, expectation_points)
                ]
            self.assertTrue(make_polygon_mock.call_args[0][0], "segment_class")

    def test_throws_on_unknown_type(self):
        try:
            _parse_annotation(self.parsed_json["annotations"][3])  # 3 is an unsupported type
        except UnsupportedImportAnnotationType as e:
            self.assertEqual(e.import_type, "dataloop")
            self.assertEqual(e.annotation_type, "UNSUPPORTED_TYPE")
        except Exception as e:
            self.fail(f"Test threw wrong exception: {e}")
