import asyncio
from pathlib import Path, PosixPath, WindowsPath
from tempfile import TemporaryDirectory
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from darwin.dataset.upload_manager import LocalFile
from darwin.future.core.client import ClientCore
from darwin.future.exceptions import DarwinException
from darwin.future.meta.objects.workflow import Workflow
from darwin.future.tests.core.fixtures import *


@patch("darwin.future.meta.objects.workflow.asyncio")
@patch.object(Workflow, "upload_files_async")
def test_upload_files(mock_upload_files_async: Mock, mock_asyncio: Mock):
    mock_asyncio.run = mock.MagicMock()

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

    mock_asyncio.run.assert_called_once()


@patch.object(Workflow, "upload_files_async")
def test_upload_files_raises(mock_upload_files_async: Mock):
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
def test_upload_files_async():
    ...


# Test `_get_item_path`
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
def test_with_no_internal_folder_structure(imposed_path: str, preserve_folders: bool, expectation: str) -> None:
    with TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "file1.jpg"
        open(file_path, "w").close()

        path: str = Workflow._get_item_path(
            file_path,
            Path(tmpdir),
            imposed_path,
            preserve_folders,
        )

        assert path == expectation


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
def test_with_internal_folder_structure(imposed_path: str, preserve_folders: bool, expectation: str) -> None:
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


# Test `_derive_root_path`
def test_derive_root_path():
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


def test_derive_root_path_raises():
    with pytest.raises(ValueError):
        Workflow._derive_root_path([1, 2, 3])  # type: ignore


def test_converts_list_of_paths():
    paths = asyncio.run(Workflow._convert_filelikes_to_paths(["tmp/upload/1", LocalFile("tmp/upload/2")]))

    # x-platform tolerant tests
    assert all(isinstance(path, (PosixPath, WindowsPath)) for path in paths)
    assert len(paths) == 2
    assert paths[0] == Path("tmp/upload/1")
    assert paths[1] == Path("tmp/upload/2")


def test_raises_on_invalid_input():
    with pytest.raises(TypeError):
        asyncio.run(Workflow._convert_filelikes_to_paths([1, 2, 3]))  # type: ignore


# Test `_upload_file_to_signed_url`
def test_upload_file_to_signed_url(base_client: ClientCore) -> None:
    url = "https://example.com/signed-url"
    file = Path("test.txt")

    class Response:
        ok: bool = True

    with patch("darwin.future.meta.objects.workflow.async_upload_file", return_value=Response()) as mock_upload_file:
        workflow = Workflow(base_client, MagicMock(), MagicMock())
        result = asyncio.run(workflow._upload_file_to_signed_url(url, file))

        mock_upload_file.assert_called_once_with(base_client, url, file)
        assert result.ok is True


def test_upload_file_to_signed_url_raises(base_client: ClientCore) -> None:
    url = "https://example.com/signed-url"
    file = Path("test.txt")

    class Response:
        ok: bool = False

    with patch("darwin.future.meta.objects.workflow.async_upload_file", return_value=Response):
        with pytest.raises(DarwinException):
            workflow = Workflow(base_client, MagicMock(), MagicMock())
            asyncio.run(workflow._upload_file_to_signed_url(url, file))
