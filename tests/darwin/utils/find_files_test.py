from dataclasses import dataclass
from pathlib import Path, PosixPath
from typing import Any, Callable, Dict, List, Optional
from unittest import TestCase, skip
from unittest.mock import MagicMock, patch

from darwin.exceptions import UnsupportedFileType
from darwin.utils import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
    find_files,
    is_extension_allowed,
)


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
    @patch("darwin.utils.is_extension_allowed_by_filename", return_value=True)
    def test_find_files_returns_a_list_of_files(self, mock_is_extension_allowed):
        output = find_files(self.fake_files, files_to_exclude=[], recursive=False)

        self.assertIsInstance(output, list)
        [self.assertIsInstance(file, Path) for file in output]

    @patch("darwin.utils.is_extension_allowed_by_filename", return_value=True)
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

    @patch("darwin.utils.is_extension_allowed_by_filename", return_value=False)
    def test_raises_error_unsupported_filetype(self, mock_is_extension_allowed):
        with self.assertRaises(UnsupportedFileType):
            find_files(["1"], files_to_exclude=[], recursive=False)

    @patch("darwin.utils.is_extension_allowed_by_filename")
    def test_uses_correct_glob_if_recursive(self, mock_is_extension_allowed):
        with patch("darwin.utils.Path.is_dir") as mock_is_dir:
            with patch("darwin.utils.Path.glob") as mock_glob:
                mock_is_dir.return_value = True
                mock_glob.return_value = ["1"]

                find_files(["123"], files_to_exclude=[], recursive=True)

                self.assertTrue(mock_glob.called)
                self.assertEqual(mock_glob.call_args[0][0], "**/*")

    @patch("darwin.utils.is_extension_allowed_by_filename")
    def test_glob_results_in_correct_call_to_is_extension_allowed_by_filename(self, mock_is_extension_allowed):
        mock_is_extension_allowed.return_value = True
        with patch("darwin.utils.Path.is_dir") as mock_is_dir:
            with patch("darwin.utils.Path.glob") as mock_glob:
                mock_is_dir.return_value = True
                mock_glob.return_value = [Path("1.png"), Path("1/b/c/2.png"), Path("1/b/c/3.png")]

                result = find_files(["1"], files_to_exclude=[], recursive=True)

                self.assertEqual(
                    result,
                    [
                        PosixPath("1.png"),
                        PosixPath("1/b/c/2.png"),
                        PosixPath("1/b/c/3.png"),
                    ],
                )

    @patch("darwin.utils.is_extension_allowed_by_filename")
    def test_uses_correct_glob_if_not_recursive(self, mock_is_extension_allowed):
        with patch("darwin.utils.Path.is_dir") as mock_is_dir:
            with patch("darwin.utils.Path.glob") as mock_glob:
                mock_is_dir.return_value = True
                mock_glob.return_value = ["1"]

                find_files(["1"], files_to_exclude=[], recursive=False)

                self.assertTrue(mock_glob.called)
                self.assertEqual(mock_glob.call_args[0][0], "*")


class TestIsExtensionAllowedByFilenameFunctions(FindFileTestCase):
    @dataclass
    class Dependencies:
        ieabf: Optional[Callable[[str], bool]] = None
        iveabf: Optional[Callable[[str], bool]] = None
        iieabf: Optional[Callable[[str], bool]] = None

    def dependency_factory(self) -> Dependencies:
        """
        Dependency injection factory that allows different instantions of the dependencies
        to avoid race condition failures and flaky tests.

        returns: Dependencies
        """
        from darwin.utils import is_extension_allowed_by_filename as ieabf
        from darwin.utils import is_image_extension_allowed_by_filename as iieabf
        from darwin.utils import is_video_extension_allowed_by_filename as iveabf

        return self.Dependencies(ieabf=ieabf, iveabf=iveabf, iieabf=iieabf)

    def test_ieabf_returns_true_for_a_valid_extension(self):
        valid_extensions = [*self.fake_supported_files, *self.fake_supported_files_varied_case]
        results = [self.dependency_factory().ieabf(file) for file in valid_extensions]

        self.assertTrue(all(results))

    def test_ieabf_returns_false_for_an_invalid_extension(self):
        results = [self.dependency_factory().ieabf(file) for file in self.fake_invalid_files]

        self.assertFalse(all(results))

    def test_iveabf_returns_true_for_a_valid_extension(self):
        results = [self.dependency_factory().iveabf(file) for file in SUPPORTED_VIDEO_EXTENSIONS]

        self.assertTrue(all(results))

    def test_iveabf_returns_false_for_an_invalid_extension(self):
        results = [self.dependency_factory().iveabf(file) for file in self.fake_invalid_files]

        self.assertFalse(all(results))

    def test_iieabf_returns_true_for_a_valid_extension(self):
        results = [self.dependency_factory().iieabf(file) for file in SUPPORTED_IMAGE_EXTENSIONS]

        self.assertTrue(all(results))

    def test_iieabf_returns_false_for_an_invalid_extension(self):
        results = [self.dependency_factory().iieabf(file) for file in self.fake_invalid_files]

        self.assertFalse(all(results))
