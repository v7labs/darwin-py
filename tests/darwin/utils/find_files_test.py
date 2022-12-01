from pathlib import Path, PosixPath
from typing import List
from unittest import TestCase, skip
from unittest.mock import MagicMock, patch

from darwin.exceptions import UnsupportedFileType
from darwin.utils import SUPPORTED_EXTENSIONS, find_files, is_extension_allowed


class FindFileTestCase(TestCase):
    fake_invalid_files = [
        "/testdir.invalidextension",
        "/testdir/testdir2.invalidextension",
    ]
    fake_supported_files = [f"testdir/testfile{ext}" for ext in SUPPORTED_EXTENSIONS]
    fake_supported_files_varied_case = [f"testdir/testdir2/testfile{ext.upper()}" for ext in SUPPORTED_EXTENSIONS]
    fake_files = [
        "testdir/testdir2/testfile.png",
        "testdir/testdir2/testfile2.png",
        "testdir/testfile.png",
        *fake_supported_files,
        *fake_supported_files_varied_case,
    ]
    fake_file_expected_length = len(fake_files) - len(fake_invalid_files)

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()


class TestFindFiles(FindFileTestCase):
    @patch("darwin.utils.is_extension_allowed", return_value=True)
    def test_find_files_returns_a_list_of_files(self, mock_is_extension_allowed):
        output = find_files(self.fake_files, files_to_exclude=[], recursive=False)

        self.assertIsInstance(output, list)
        [self.assertIsInstance(file, Path) for file in output]

    @patch("darwin.utils.is_extension_allowed", return_value=True)
    def test_find_files_excludes_files_in_excluded_list(self, mock_is_extension_allowed):
        output = find_files(
            self.fake_files,
            files_to_exclude=[
                "testdir/testdir2/testfile.png",
                "testdir/testdir2/testfile2.png",
            ],
            recursive=False,
        )

        self.assertEqual(len(self.fake_files) - 2, len(output))

    @patch("darwin.utils.is_extension_allowed", return_value=False)
    def test_raises_error_unsupported_filetype(self, mock_is_extension_allowed):
        with self.assertRaises(UnsupportedFileType):
            find_files(["1"], files_to_exclude=[], recursive=False)

    @patch("darwin.utils.Path", autospec=True)
    @patch("darwin.utils.is_extension_allowed")
    def test_uses_correct_glob_if_recursive(self, mock_is_extension_allowed, mock_path):
        mock_path.is_dir.return_value = True
        mock_path.glob.return_value = ["1"]

        find_files(["1"], files_to_exclude=[], recursive=True)

        mock_path.return_value.glob.assert_called_once_with("**/*")

    @patch("darwin.utils.Path", autospec=True)
    @patch("darwin.utils.is_extension_allowed")
    def test_uses_correct_glob_if_not_recursive(self, mock_is_extension_allowed, mock_path):
        mock_path.is_dir.return_value = True
        mock_path.glob.return_value = ["1"]

        find_files(["1"], files_to_exclude=[], recursive=False)

        mock_path.return_value.glob.assert_called_once_with("*")


class TestIsExtensionAllowed(FindFileTestCase):
    def test_returns_true_for_a_valid_extension(self):
        for file in [*self.fake_supported_files, *self.fake_supported_files_varied_case]:
            with self.subTest(file=file):
                print(file)
                self.assertTrue(is_extension_allowed(file))

    def test_returns_false_for_an_invalid_extension(self):
        for file in self.fake_invalid_files:
            with self.subTest(file=file):
                self.assertFalse(is_extension_allowed(file))
