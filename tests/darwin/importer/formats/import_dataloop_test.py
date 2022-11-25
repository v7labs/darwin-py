from os.path import dirname, join, realpath
from pathlib import Path
from typing import Dict
from unittest import TestCase, skip
from unittest.mock import MagicMock, Mock, patch

from darwin.importer.formats.dataloop import (
    _parse_annotation,
    _remove_leading_slash,
    parse_path,
)


class DataLoopTestCase(TestCase):
    def setUp(self):
        _fd = open(realpath(join(dirname(__file__), "..", "..", "data", "dataloop.example.json")))
        self.DATALOOP_MOCK_DATA = _fd.read()
        _fd.close()

    DARWIN_PARSED_DATA = {
        "filename": "test.jpg",
        "annotations": [
            {"class": "class_1"},
            {"class": "class_2"},
            {"class": "class_3"},
        ],
    }


class TestParsePath(DataLoopTestCase):
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

        _parse_annotation_mock.assert_called_once()
        path_open_mock.assert_called_once()
        json_load_mock.assert_called_once()
        mock_remove_leading_slash.assert_called_once()


class TestRemoveLeadingSlash(DataLoopTestCase):
    def test_removes_slash_if_present(self):
        self.assertEqual(_remove_leading_slash("/foo"), "foo")

    def test_does_not_remove_slash_if_not_present(self):
        self.assertEqual(_remove_leading_slash("foo"), "foo")


class TestParseAnnotation(DataLoopTestCase):
    @skip("Not yet implemented")
    def test_handles_box_type(self):
        ...

    @skip("Not yet implemented")
    def test_handles_class_type(self):
        ...

    @skip("Not yet implemented")
    def test_handles_segment_type(self):
        ...
