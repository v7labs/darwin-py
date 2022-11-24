from os.path import dirname, join
from unittest import TestCase, skip
from unittest.mock import patch

from darwin.importer.formats.dataloop import (
    _parse_annotation,
    _remove_leading_slash,
    parse_path,
)


class DataLoopTestCase(TestCase):
    dataloop_mock_data_fd = open(join(dirname(__file__), "dataloop_mock_data.json"))
    dataloop_mock_data = dataloop_mock_data_fd.read()
    dataloop_mock_data_fd.close()
    del dataloop_mock_data_fd


class TestParsePath(DataLoopTestCase):
    def test_returns_none_if_file_extension_is_not_json(self):
        self.assertIsNone(parse_path("foo.bar"))

    @skip("WIP")
    def test_opens_with_list_of_annotations(self):
        with patch("darwin.importer.formats.dataloop.pathlib.Path.open") as mock_open:
            mock_open.return_value.return_value = self.dataloop_mock_data

            parse_path("foo.json")
            mock_open.assert_called_with("foo.json")
        # TODO: Continue here

    @skip("WIP")
    def test_returns_only_one_of_each_annotation_class(self):
        ...


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
