import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from unittest.mock import Mock, patch

import pytest

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.item import (
    ItemCreate,
    ItemSlot,
    ItemUpload,
    ItemUploadStatus,
    UploadItem,
)
from darwin.future.exceptions import DarwinException
from darwin.future.meta.meta_uploader import (
    _confirm_uploads,
    _create_list_of_all_files,
    _derive_root_path,
    _get_item_path,
    _handle_uploads,
    _initial_items_and_blocked_items,
    _initialise_item_uploads,
    _initialise_items_and_paths,
    _item_dict_to_item,
    _items_dicts_to_items,
    _prepare_upload_items,
    _update_item_upload,
    _upload_file_to_signed_url,
    combined_uploader,
)
from darwin.future.tests.fixtures import *
from darwin.future.tests.meta.fixtures import *


@pytest.fixture
def mock_file(tmp_path: Path) -> Path:
    file = tmp_path / "file1.jpg"
    file.touch()
    return file


@pytest.fixture
def mock_dir(tmp_path: Path) -> Path:
    dir = tmp_path / "dir1"
    dir.mkdir()
    return dir


@pytest.fixture
def mock_files(tmp_path: Path) -> List[Path]:
    files = [
        tmp_path / "file1.jpg",
        tmp_path / "file2.jpg",
        tmp_path / "file3.jpg",
    ]
    for file in files:
        file.touch()

    return files


class TestGetItemPath:
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
            file_path = Path(tmpdir) / "file1.jpg"
            open(file_path, "w").close()

            path: str = _get_item_path(
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
    def test_with_internal_folder_structure(self, imposed_path: str, preserve_folders: bool, expectation: str) -> None:
        with TemporaryDirectory() as tmpdir:
            tmpdir_inner_path = Path(tmpdir) / "folder1"
            tmpdir_inner_path.mkdir(parents=True, exist_ok=True)
            file_path = Path(tmpdir_inner_path) / "file1.jpg"
            file_path.open("w").close()

            path: str = _get_item_path(
                file_path,
                Path(tmpdir),
                imposed_path,
                preserve_folders,
            )

            assert path == expectation


class TestPrepareUploadItems:
    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader._get_item_path", return_value="/")
    @patch.object(Path, "is_dir")
    @patch.object(Path, "is_file")
    @patch.object(Path, "is_absolute")
    async def test_happy_path(
        self,
        is_absolute: Mock,
        is_file: Mock,
        is_dir: Mock,
        _: Mock,
        mock_dir: Path,
        mock_files: List[Path],
    ) -> None:
        is_dir.return_value = True
        is_file.return_value = True
        is_absolute.return_value = True

        result = await _prepare_upload_items(
            "/",
            mock_dir,
            mock_files,
            False,
            False,
            False,
            False,
        )

        assert all(r.name == f"file{i+1}.jpg" for i, r in enumerate(result))
        assert all(r.path == "/" for r in result)

        assert result[0].slots[0].slot_name == "1"
        assert result[0].slots[0].file_name == "file1.jpg"
        assert result[0].slots[0].as_frames is False
        assert result[0].slots[0].fps is False
        assert result[0].slots[0].extract_views is False

        assert result[1].slots[0].slot_name == "2"
        assert result[1].slots[0].file_name == "file2.jpg"
        assert result[1].slots[0].as_frames is False
        assert result[1].slots[0].fps is False
        assert result[1].slots[0].extract_views is False

        assert result[2].slots[0].slot_name == "3"
        assert result[2].slots[0].file_name == "file3.jpg"
        assert result[2].slots[0].as_frames is False
        assert result[2].slots[0].fps is False
        assert result[2].slots[0].extract_views is False

        assert all(r.tags == [] for r in result)
        assert all(r.description is None for r in result)
        assert all(r.layout is None for r in result)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exists_return, is_dir_return, is_file_return, is_absolute_return, expectation",
        [
            (False, True, True, True, "root_path must be a directory"),
            (True, False, True, True, "file_paths must be absolute paths"),
            (True, True, False, True, "file_paths must be absolute paths"),
            (True, True, True, False, "file_paths must be absolute paths"),
        ],
    )
    @patch.object(Path, "exists")
    @patch.object(Path, "is_dir")
    @patch.object(Path, "is_file")
    @patch.object(Path, "is_absolute")
    async def test_asserts(
        self,
        is_absolute: Mock,
        is_file: Mock,
        is_dir: Mock,
        exists: Mock,
        exists_return: bool,
        is_dir_return: bool,
        is_file_return: bool,
        is_absolute_return: bool,
        expectation: str,
        mock_file: Path,
        mock_dir: Path,
        mock_files: List[Path],
    ) -> None:
        exists.return_value = exists_return
        is_dir.return_value = is_dir_return
        is_file.return_value = is_file_return
        is_absolute.return_value = is_absolute_return

        with pytest.raises(AssertionError) as e:
            await _prepare_upload_items(
                "/",
                mock_dir,
                mock_files,
                False,
                False,
                False,
                False,
            )

            assert expectation in str(e.value)


class TestDeriveRootPath:
    def test_derive_root_path(self):
        root_path, absolute_path = _derive_root_path(
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
        with pytest.raises(ValueError):
            _derive_root_path([1, 2, 3])  # type: ignore


class TestUploadFileToSignedUrl:
    @pytest.mark.asyncio
    async def test_upload_file_to_signed_url(self) -> None:
        url = "https://example.com/signed-url"
        file = Path("test.txt")

        class Response:
            ok: bool = True

        with patch("darwin.future.meta.meta_uploader.async_upload_file", return_value=Response()) as mock_upload_file:
            result = await _upload_file_to_signed_url(url, file)

            mock_upload_file.assert_called_once_with(url, file)
            assert result.ok is True

    @pytest.mark.asyncio
    async def test_upload_file_to_signed_url_raises(self) -> None:
        url = "https://example.com/signed-url"
        file = Path("test.txt")

        class Response:
            ok: bool = False

        with patch("darwin.future.meta.meta_uploader.async_upload_file", return_value=Response):
            with pytest.raises(DarwinException):
                await _upload_file_to_signed_url(url, file)


class TestCreateListOfAllFiles:
    ...  # TODO


class TestInitialiseItemUploads:
    def test_initialise_item_uploads(self):
        upload_items = [
            UploadItem(name="file1.txt", path="/path/to/file1.txt"),
            UploadItem(name="file2.txt", path="/path/to/file2.txt"),
            UploadItem(name="file3.txt", path="/path/to/file3.txt"),
        ]
        expected = [
            ItemUpload(upload_item=upload_items[0], status=ItemUploadStatus.PENDING),
            ItemUpload(upload_item=upload_items[1], status=ItemUploadStatus.PENDING),
            ItemUpload(upload_item=upload_items[2], status=ItemUploadStatus.PENDING),
        ]
        assert _initialise_item_uploads(upload_items) == expected


class TestInitialiseItemsAndPaths:
    def test_with_preserve_paths(self):
        upload_items = [
            UploadItem(
                name="file1.txt",
                path="/path/to/file1.txt",
                description="file1 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
            UploadItem(
                name="file2.txt",
                path="/path/to/file2.txt",
                description="file2 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
            UploadItem(
                name="file3.txt",
                path="/path/to/file3.txt",
                description="file3 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
        ]
        root_path_absolute = Path("/tmp/example/test/path")
        item_payload = ItemCreate(
            files=[
                Path("/path/to/file1.txt"),
                Path("/path/to/file2.txt"),
                Path("/path/to/file3.txt"),
            ],
            preserve_folders=True,
        )
        expected_output = [
            (
                UploadItem(
                    name="file1.txt",
                    path="/path/to/file1.txt",
                    description="file1 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/tmp/example/test/path"),
            ),
            (
                UploadItem(
                    name="file2.txt",
                    path="/path/to/file2.txt",
                    description="file2 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/tmp/example/test/path"),
            ),
            (
                UploadItem(
                    name="file3.txt",
                    path="/path/to/file3.txt",
                    description="file3 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/tmp/example/test/path"),
            ),
        ]
        assert _initialise_items_and_paths(upload_items, root_path_absolute, item_payload) == expected_output

    def test_without_preserve_folders(self):
        upload_items = [
            UploadItem(
                name="file1.txt",
                path="/path/to/file1.txt",
                description="file1 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
            UploadItem(
                name="file2.txt",
                path="/path/to/file2.txt",
                description="file2 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
            UploadItem(
                name="file3.txt",
                path="/path/to/file3.txt",
                description="file3 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
        ]
        root_path_absolute = Path("/tmp/example/test/path")
        item_payload = ItemCreate(
            files=[
                Path("/path/to/file1.txt"),
                Path("/path/to/file2.txt"),
                Path("/path/to/file3.txt"),
            ],
            preserve_folders=False,
        )
        expected_output = [
            (
                UploadItem(
                    name="file1.txt",
                    path="/",
                    description="file1 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/tmp/example/test/path"),
            ),
            (
                UploadItem(
                    name="file2.txt",
                    path="/",
                    description="file2 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/tmp/example/test/path"),
            ),
            (
                UploadItem(
                    name="file3.txt",
                    path="/",
                    description="file3 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/tmp/example/test/path"),
            ),
        ]
        assert _initialise_items_and_paths(upload_items, root_path_absolute, item_payload) == expected_output
