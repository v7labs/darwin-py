import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List
from unittest.mock import Mock, patch

import pytest
from cv2 import fastNlMeansDenoisingMulti

from darwin.future.data_objects.item import ItemSlot, UploadItem
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
        get_item_path: Mock,
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

        assert result == [
            UploadItem(
                name="file1.jpg",
                path="/",
                slots=[ItemSlot(slot_name="1", file_name="file1.jpg", as_frames=False, fps=False, extract_views=False)],
                tags=[],
                description=None,
                layout=None,
            ),
            UploadItem(
                name="file2.jpg",
                path="/",
                slots=[ItemSlot(slot_name="1", file_name="file2.jpg", as_frames=False, fps=False, extract_views=False)],
                tags=[],
                description=None,
                layout=None,
            ),
            UploadItem(
                name="file3.jpg",
                path="/",
                slots=[ItemSlot(slot_name="1", file_name="file3.jpg", as_frames=False, fps=False, extract_views=False)],
                tags=[],
                description=None,
                layout=None,
            ),
        ]

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


# @patch.object(Workflow, "upload_files_async")
# def test_upload_files_raises(mock_upload_files_async: Mock):
#     mock_upload_files_async.side_effect = Exception("Error")

#     with pytest.raises(Exception):
#         Workflow.upload_files(
#             MagicMock(),
#             ["file1", "file2"],
#             ["file3"],
#             24,
#             "tmp",
#             True,
#             True,
#             True,
#             True,
#         )


# # Test upload_files_async
# from typing import Optional


# class ContextReturn:
#     mock_convert_filelikes_to_paths: Optional[Mock]
#     mock_derive_root_path: Optional[Mock]
#     mock_prepare_upload_items: Optional[Mock]
#     mock_upload_updateable: Optional[Mock]
#     mock_async_register_and_create_signed_upload_url: Optional[Mock]

#     def __init__(
#         self,
#         mock_convert_filelikes_to_paths: Optional[Mock] = None,
#         mock_derive_root_path: Optional[Mock] = None,
#         mock_prepare_upload_items: Optional[Mock] = None,
#         mock_upload_updateable: Optional[Mock] = None,
#         mock_async_register_and_create_signed_upload_url: Optional[Mock] = None,
#     ):
#         self.mock_convert_filelikes_to_paths = mock_convert_filelikes_to_paths
#         self.mock_derive_root_path = mock_derive_root_path
#         self.mock_prepare_upload_items = mock_prepare_upload_items
#         self.mock_upload_updateable = mock_upload_updateable
#         self.mock_async_register_and_create_signed_upload_url = mock_async_register_and_create_signed_upload_url


# @contextmanager
# def upload_function_test_context(workflow: Workflow) -> Generator[ContextReturn, None, None]:
#     with patch.object(workflow, "_convert_filelikes_to_paths") as mock_convert_filelikes_to_paths, patch.object(
#         workflow, "_derive_root_path"
#     ) as mock_derive_root_path, patch.object(
#         workflow, "_prepare_upload_items"
#     ) as mock_prepare_upload_items, patch.object(
#         workflow, "_upload_updateable"
#     ) as mock_upload_updateable, patch(
#         "darwin.future.meta.objects.workflow.async_register_and_create_signed_upload_url"
#     ) as mock_async_register_and_create_signed_upload_url:
#         yield ContextReturn(
#             mock_convert_filelikes_to_paths,
#             mock_derive_root_path,
#             mock_prepare_upload_items,
#             mock_upload_updateable,
#             mock_async_register_and_create_signed_upload_url,
#         )

#         return None


# def test_upload_files_async_raises_if_no_dataset(base_client: ClientCore) -> None:
#     workflow = Workflow(MagicMock(), base_client, MagicMock())
#     workflow._element.dataset = None

#     with pytest.raises(AssertionError):
#         asyncio.run(
#             workflow.upload_files_async(
#                 ["file1", "file2"],
#                 ["file3"],
#                 24,
#                 "tmp",
#                 False,
#                 False,
#                 False,
#                 False,
#             )
#         )


# def test_upload_files_integrates_methods(base_client: ClientCore) -> None:
#     workflow = Workflow(MagicMock(), base_client, MagicMock())

#     with upload_function_test_context(workflow) as context:
#         asyncio.run(
#             workflow.upload_files_async(
#                 ["file1", "file2"],
#                 ["file3"],
#                 24,
#                 "tmp",
#                 False,
#                 False,
#                 False,
#                 False,
#             )
#         )

#         assert context.mock_async_register_and_create_signed_upload_url is not None
#         context.mock_async_register_and_create_signed_upload_url.assert_called_once()

#         assert context.mock_convert_filelikes_to_paths is not None
#         context.mock_convert_filelikes_to_paths.assert_called_once()

#         assert context.mock_derive_root_path is not None
#         context.mock_derive_root_path.assert_called_once()

#         assert context.mock_prepare_upload_items is not None
#         context.mock_prepare_upload_items.assert_called_once()

#         assert context.mock_upload_updateable is not None
#         context.mock_upload_updateable.assert_called_once()


# @pytest.mark.parametrize(
#     "imposed_path, preserve_folders, expectation",
#     [
#         # Seems like a lot of these, but together they cover scenarios that
#         # _do_ fail in very specific groups if the function is wrong
#         ("/", False, "/"),
#         ("/test", False, "/test"),
#         ("test", False, "/test"),
#         ("test/", False, "/test"),
#         ("test/test2", False, "/test/test2"),
#         ("test/test2/", False, "/test/test2"),
#         ("/", True, "/folder1"),
#         ("/test", True, "/test/folder1"),
#         ("test", True, "/test/folder1"),
#         ("test/", True, "/test/folder1"),
#         ("test/test2", True, "/test/test2/folder1"),
#         ("test/test2/", True, "/test/test2/folder1"),
#     ],
# )
# def test_with_internal_folder_structure(imposed_path: str, preserve_folders: bool, expectation: str) -> None:
#     with TemporaryDirectory() as tmpdir:
#         tmpdir_inner_path = Path(tmpdir) / "folder1"
#         tmpdir_inner_path.mkdir(parents=True, exist_ok=True)
#         file_path = Path(tmpdir_inner_path) / "file1.jpg"
#         file_path.open("w").close()

#         path: str = Workflow._get_item_path(
#             file_path,
#             Path(tmpdir),
#             imposed_path,
#             preserve_folders,
#         )

#         assert path == expectation


# # Test `_derive_root_path`
# def test_derive_root_path():
#     root_path, absolute_path = Workflow._derive_root_path(
#         [
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9/10/11"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9/10"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8/9"),
#             Path("tmp/upload"),
#             Path("tmp/upload/1/2/3/4/5/6/7/8"),
#             Path("tmp/upload/1/2/3/4/5/6/7"),
#             Path("tmp/upload/1/2/3/4/5/6"),
#             Path("tmp/upload/1/2/3/4/5"),
#             Path("tmp/upload/1/2/3/4"),
#             Path("tmp/upload/1/2/3"),
#             Path("tmp/upload/1/2"),
#             Path("tmp/upload/1"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14/15"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13/14"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12/13"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11/12"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10/11"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9/10"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8/9"),
#             Path("/tmp/upload"),
#             Path("/tmp/upload/1/2/3/4/5/6/7/8"),
#             Path("/tmp/upload/1/2/3/4/5/6/7"),
#             Path("/tmp/upload/1/2/3/4/5/6"),
#             Path("/tmp/upload/1/2/3/4/5"),
#             Path("/tmp/upload/1/2/3/4"),
#             Path("/tmp/upload/1/2/3"),
#             Path("/tmp/upload/1/2"),
#             Path("/tmp/upload/1"),
#         ]
#     )

#     assert str(root_path) == "upload"
#     assert str(absolute_path) == str(Path.cwd() / "upload")


# def test_derive_root_path_raises():
#     with pytest.raises(ValueError):
#         Workflow._derive_root_path([1, 2, 3])  # type: ignore


# # Test `_convert_filelikes_to_paths`
# def test_converts_list_of_paths():
#     paths = asyncio.run(Workflow._convert_filelikes_to_paths(["tmp/upload/1", LocalFile("tmp/upload/2")]))

#     # x-platform tolerant tests
#     assert all(isinstance(path, (PosixPath, WindowsPath)) for path in paths)
#     assert len(paths) == 2
#     assert paths[0] == Path("tmp/upload/1")
#     assert paths[1] == Path("tmp/upload/2")


# def test_raises_on_invalid_input():
#     with pytest.raises(TypeError):
#         asyncio.run(Workflow._convert_filelikes_to_paths([1, 2, 3]))  # type: ignore


# # Test `_upload_file_to_signed_url`
# def test_upload_file_to_signed_url(base_client: ClientCore) -> None:
#     url = "https://example.com/signed-url"
#     file = Path("test.txt")

#     class Response:
#         ok: bool = True

#     with patch("darwin.future.meta.objects.workflow.async_upload_file", return_value=Response()) as mock_upload_file:
#         workflow = Workflow(MagicMock(), MagicMock(), MagicMock())
#         result = asyncio.run(workflow._upload_file_to_signed_url(url, file))

#         mock_upload_file.assert_called_once_with(workflow.client, url, file)
#         assert result.ok is True


# def test_upload_file_to_signed_url_raises(base_client: ClientCore) -> None:
#     url = "https://example.com/signed-url"
#     file = Path("test.txt")

#     class Response:
#         ok: bool = False

#     with patch("darwin.future.meta.objects.workflow.async_upload_file", return_value=Response):
#         with pytest.raises(DarwinException):
#             workflow = Workflow(base_client, MagicMock(), MagicMock())
#             asyncio.run(workflow._upload_file_to_signed_url(url, file))
