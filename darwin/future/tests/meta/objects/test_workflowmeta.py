import asyncio
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

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
