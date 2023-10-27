import platform
from pathlib import Path, PosixPath, WindowsPath
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch

import pytest

from darwin.dataset.upload_manager import LocalFile
from darwin.future.meta.objects.workflow import Workflow


class TestWorkflowMeta:
    class TestUploadFiles:
        @patch.object(Workflow, "upload_files_async")
        def test_upload_files(self, mock_upload_files_async: Mock):
            Workflow.upload_files(
                MagicMock(),
                ["file1", "file2"],
                ["file3"],
                24,
                "tmp",
                True,
                True,
                True,
                True,
            )

            mock_upload_files_async.assert_called_once_with(
                ["file1", "file2"],
                ["file3"],
                24,
                "tmp",
                True,
                True,
                True,
                True,
            )

        @patch.object(Workflow, "upload_files_async")
        def test_upload_files_raises(self, mock_upload_files_async: Mock):
            mock_upload_files_async.side_effect = Exception("Error")

            with pytest.raises(Exception):
                Workflow.upload_files(
                    MagicMock(),
                    ["file1", "file2"],
                    ["file3"],
                    24,
                    "tmp",
                    True,
                    True,
                    True,
                    True,
                )

    # TODO Test upload_files_async
    class TestUploadFilesAsync:
        ...

    class TestGetItemPath:
        class TestWithoutPreserveFolders:
            @pytest.mark.parametrize(
                "imposed_path, preserve_folders, expectation",
                [
                    ("/", False, "/"),
                    ("/test", False, "/test"),
                    ("test", False, "/test"),
                    ("test/", False, "/test"),
                    ("test/test2", False, "/test/test2"),
                    ("test/test2/", False, "/test/test2"),
                    ("/", True, "/"),
                    ("/test", True, "/test"),
                    ("test", True, "/test"),
                    ("test/", True, "/test"),
                    ("test/test2", True, "/test/test2"),
                    ("test/test2/", True, "/test/test2"),
                ],
            )
            def test_with_no_internal_folder_structure(
                self, imposed_path: str, preserve_folders: bool, expectation: str
            ) -> None:
                with TemporaryDirectory() as tmpdir:
                    open(tmpdir + "/file1.jpg", "w").close()

                    path: str = Workflow._get_item_path(
                        Path(tmpdir + "/file1.jpg"),
                        Path(tmpdir),
                        "/",
                        False,
                    )

                    assert path == "/"

            @pytest.mark.parametrize(
                "imposed_path, preserve_folders, expectation",
                [
                    # Seems like a lot of these, but together they cover scenarios that
                    # _do_ fail in very specific groups if the function is wrong
                    ("/", False, "/"),
                    ("/test", False, "/test"),
                    ("test", False, "/test"),
                    ("test/", False, "/test"),
                    ("test/test2", False, "/test/test2"),
                    ("test/test2/", False, "/test/test2"),
                    ("/", True, "/folder1"),
                    ("/test", True, "/test/folder1"),
                    ("test", True, "/test/folder1"),
                    ("test/", True, "/test/folder1"),
                    ("test/test2", True, "/test/test2/folder1"),
                    ("test/test2/", True, "/test/test2/folder1"),
                ],
            )
            def test_with_internal_folder_structure(
                self, imposed_path: str, preserve_folders: bool, expectation: str
            ) -> None:
                with TemporaryDirectory() as tmpdir:
                    tmpdir_inner_path = Path(tmpdir) / "folder1"
                    tmpdir_inner_path.mkdir(parents=True, exist_ok=True)
                    file_path = Path(tmpdir_inner_path) / "file1.jpg"
                    file_path.open("w").close()

                    path: str = Workflow._get_item_path(
                        file_path,
                        Path(tmpdir),
                        imposed_path,
                        preserve_folders,
                    )

                    assert path == expectation

    class TestDeriveRootPath:
        def test_derive_root_path(self):
            root_path, absolute_path = Workflow._derive_root_path(
                [
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9/10"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8/9"),
                    Path("tmp/upload"),
                    Path("tmp/upload/1/2/3/4/5/6/7/8"),
                    Path("tmp/upload/1/2/3/4/5/6/7"),
                    Path("tmp/upload/1/2/3/4/5/6"),
                    Path("tmp/upload/1/2/3/4/5"),
                    Path("tmp/upload/1/2/3/4"),
                    Path("tmp/upload/1/2/3"),
                    Path("tmp/upload/1/2"),
                    Path("tmp/upload/1"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8/9"),
                    Path("/tmp/upload"),
                    Path("/tmp/upload/1/2/3/4/5/6/7/8"),
                    Path("/tmp/upload/1/2/3/4/5/6/7"),
                    Path("/tmp/upload/1/2/3/4/5/6"),
                    Path("/tmp/upload/1/2/3/4/5"),
                    Path("/tmp/upload/1/2/3/4"),
                    Path("/tmp/upload/1/2/3"),
                    Path("/tmp/upload/1/2"),
                    Path("/tmp/upload/1"),
                ]
            )

            assert str(root_path) == "upload"
            assert str(absolute_path) == str(Path.cwd() / "upload")

        def test_derive_root_path_raises(self):
            ...

    class TestConvertFilelikesToPaths:
        def test_converts_list_of_paths(self):
            paths = Workflow._convert_filelikes_to_paths(["tmp/upload/1", LocalFile("tmp/upload/2")])

            # x-platform tolerant tests
            if platform.architecture == "Windows":
                assert paths == [WindowsPath("tmp/upload/1"), WindowsPath("tmp/upload/2")]
            else:
                assert paths == [PosixPath("tmp/upload/1"), PosixPath("tmp/upload/2")]

        def test_raises_on_invalid_input(self):
            with pytest.raises(TypeError):
                Workflow._convert_filelikes_to_paths([1, 2, 3])  # type: ignore

    class TestGetFilesToUpload:
        ...
