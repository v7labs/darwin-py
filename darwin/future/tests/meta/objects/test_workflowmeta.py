import asyncio
import platform
from pathlib import Path, PosixPath, WindowsPath
from unittest.mock import MagicMock, Mock, patch

import pytest

from darwin.dataset.upload_manager import LocalFile
from darwin.future.meta.objects.workflow import Workflow


class TestWorkflowMeta:
    # TODO Test upload_files_async
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

    class TestUploadFilesAsync:
        ...

    class TestDeriveRootPath:
        def test_derive_root_path(self):
            root_path, absolute_path = asyncio.run(
                Workflow._derive_root_path(
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
            )

            assert str(root_path) == "upload"
            assert str(absolute_path) == str(Path.cwd() / "upload")

    class TestConvertFilelikesToPaths:
        def test_converts_list_of_paths(self):
            paths = asyncio.run(Workflow._convert_filelikes_to_paths(["tmp/upload/1", LocalFile("tmp/upload/2")]))

            # x-platform tolerant tests
            if platform.architecture == "Windows":
                assert paths == [WindowsPath("tmp/upload/1"), WindowsPath("tmp/upload/2")]
            else:
                assert paths == [PosixPath("tmp/upload/1"), PosixPath("tmp/upload/2")]

        def test_raises_on_invalid_input(self):
            with pytest.raises(TypeError):
                asyncio.run(Workflow._convert_filelikes_to_paths([1, 2, 3]))  # type: ignore

    class TestGetFilesToUpload:
        ...
