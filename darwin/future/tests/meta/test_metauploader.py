from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, call, patch
from uuid import UUID, uuid4

import pytest

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.data_objects.item import (
    ItemCore,
    ItemCreate,
    ItemLayout,
    ItemUpload,
    ItemUploadStatus,
    UploadItem,
)
from darwin.future.data_objects.typing import UnknownType
from darwin.future.exceptions import DarwinException, UploadPending
from darwin.future.meta.meta_uploader import (
    _confirm_uploads,
    _create_list_of_all_files,
    _derive_root_path,
    _get_item_path,
    _handle_uploads,
    _initialise_item_uploads,
    _initialise_items_and_blocked_items,
    _initialise_items_and_paths,
    _item_dict_to_item,
    _items_dicts_to_items,
    _prepare_upload_items,
    _update_item_upload,
    _upload_file_to_signed_url,
    combined_uploader,
)
from darwin.future.meta.objects.item import Item
from darwin.future.tests.core.fixtures import *
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


@pytest.fixture
def mock_upload_items() -> List[UploadItem]:
    return [
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


@pytest.fixture
def upload_ids() -> List[str]:
    return [
        "00000000-0000-0000-0000-000000000000",
        "00000000-0000-0000-0000-000000000001",
    ]


@pytest.fixture
def upload_urls() -> List[str]:
    return [
        "https://example.com/upload1",
        "https://example.com/upload2",
    ]


@pytest.fixture
def item_dicts() -> List[Dict[str, UnknownType]]:
    return [
        {
            "name": "file1.jpg",
            "id": "00000000-0000-0000-0000-000000000000",
            "slots": [],
            "path": "/path/to/file1.jpg",
            "dataset_id": 1,
            "processing_status": "pending",
        },
        {
            "name": "file2.jpg",
            "id": "00000000-0000-0000-0000-000000000001",
            "slots": [],
            "path": "/path/to/file2.jpg",
            "dataset_id": 1,
            "processing_status": "pending",
        },
    ]


@pytest.fixture
def blocked_item_dicts() -> List[Dict[str, UnknownType]]:
    return [
        {
            "name": "file3.jpg",
            "id": "00000000-0000-0000-0000-000000000002",
            "slots": [],
            "path": "/path/to/file3.jpg",
            "dataset_id": 1,
            "processing_status": "pending",
        },
        {
            "name": "file4.jpg",
            "id": "00000000-0000-0000-0000-000000000003",
            "slots": [],
            "path": "/path/to/file4.jpg",
            "dataset_id": 1,
            "processing_status": "pending",
        },
    ]


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
    @pytest.mark.asyncio
    async def test_create_list_of_all_files(self, tmp_path: Path):
        tmp_path.joinpath("file1.txt").touch()
        tmp_path.joinpath("file2.txt").touch()
        tmp_path.joinpath("file3.txt").touch()
        tmp_path.joinpath("file4.txt").touch()
        tmp_path.joinpath("file5.txt").touch()
        tmp_path.joinpath("file6.txt").touch()
        tmp_path.joinpath("file7.txt").touch()
        tmp_path.joinpath("file8.txt").touch()
        tmp_path.joinpath("file9.txt").touch()
        tmp_path.joinpath("file10.txt").touch()
        tmp_path.joinpath("file11.txt").touch()
        tmp_path.joinpath("file12.txt").touch()
        tmp_path.joinpath("file13.txt").touch()
        tmp_path.joinpath("file14.txt").touch()
        tmp_path.joinpath("file15.txt").touch()
        tmp_path.joinpath("file16.txt").touch()
        tmp_path.joinpath("file17.txt").touch()
        tmp_path.joinpath("file18.txt").touch()
        tmp_path.joinpath("file19.txt").touch()
        tmp_path.joinpath("file20.txt").touch()

        files = await _create_list_of_all_files([tmp_path], [])

        assert len(files) == 20
        assert all(isinstance(file, Path) for file in files)
        assert all(file.is_file() for file in files)

        file_names = [file.name for file in files]
        expected_file_names = [f"file{i+1}.txt" for i in range(20)]

        assert sorted(file_names) == sorted(expected_file_names)

    @pytest.mark.asyncio
    async def test_create_list_of_all_files_with_blocked_files(self, tmp_path: Path):
        tmp_path.joinpath("file1.txt").touch()
        tmp_path.joinpath("file2.txt").touch()
        tmp_path.joinpath("file3.txt").touch()
        tmp_path.joinpath("file4.txt").touch()
        tmp_path.joinpath("file5.txt").touch()
        tmp_path.joinpath("file6.txt").touch()
        tmp_path.joinpath("file7.txt").touch()
        tmp_path.joinpath("file8.txt").touch()
        tmp_path.joinpath("file9.txt").touch()
        tmp_path.joinpath("file10.txt").touch()

        blocked_files = [
            tmp_path / "file1.txt",
            tmp_path / "file2.txt",
            tmp_path / "file3.txt",
            tmp_path / "file4.txt",
            tmp_path / "file5.txt",
        ]

        files = await _create_list_of_all_files([tmp_path], blocked_files)

        assert len(files) == 5
        assert all(isinstance(file, Path) for file in files)
        assert all(file.is_file() for file in files)

        file_names = [file.name for file in files]
        expected_file_names = [f"file{i+6}.txt" for i in range(5)]

        assert sorted(file_names) == sorted(expected_file_names)

    @pytest.mark.asyncio
    async def test_create_list_of_all_files_with_multiple_directories(self, tmp_path: Path):
        tmp_path.joinpath("file1.txt").touch()
        tmp_path.joinpath("file2.txt").touch()
        tmp_path.joinpath("file3.txt").touch()
        tmp_path.joinpath("file4.txt").touch()
        tmp_path.joinpath("file5.txt").touch()
        tmp_path.joinpath("file6.txt").touch()
        tmp_path.joinpath("file7.txt").touch()
        tmp_path.joinpath("file8.txt").touch()
        tmp_path.joinpath("file9.txt").touch()
        tmp_path.joinpath("file10.txt").touch()

        tmp_path.joinpath("dir1").mkdir()
        tmp_path.joinpath("dir1").joinpath("file1.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file2.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file3.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file4.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file5.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file6.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file7.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file8.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file9.txt").touch()
        tmp_path.joinpath("dir1").joinpath("file10.txt").touch()

        tmp_path.joinpath("dir2").mkdir()
        tmp_path.joinpath("dir2").joinpath("file1.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file2.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file3.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file4.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file5.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file6.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file7.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file8.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file9.txt").touch()
        tmp_path.joinpath("dir2").joinpath("file10.txt").touch()

        files = await _create_list_of_all_files([tmp_path], [])

        assert len(files) == 30
        assert all(isinstance(file, Path) for file in files)
        assert all(file.is_file() for file in files)


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
                    path="/path/to/file1.txt",
                    description="file1 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                Path("/"),
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
                Path("/"),
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
                Path("/"),
            ),
        ]
        assert _initialise_items_and_paths(upload_items, root_path_absolute, item_payload) == expected_output


class TestUpdateItemUpload:
    @pytest.fixture
    def item_upload(self) -> ItemUpload:
        return ItemUpload(
            upload_item=UploadItem(
                name="file1.txt",
                path="/path/to/file1.txt",
                description="file1 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
            status=ItemUploadStatus.PENDING,
        )

    def test_returns_same_item(self, item_upload: ItemUpload) -> None:
        # Ensures that item is not copied to check PBR functionality
        assert id(_update_item_upload(item_upload)) == id(item_upload)

    def test_updates_status(self, item_upload: ItemUpload) -> None:
        assert _update_item_upload(item_upload, ItemUploadStatus.UPLOADING).status == ItemUploadStatus.UPLOADING

    def test_updates_upload_url(self, item_upload: ItemUpload) -> None:
        assert _update_item_upload(item_upload, upload_url="https://example.com").url == "https://example.com"

    def test_updates_upload_id(self, item_upload: ItemUpload) -> None:
        uuid1 = uuid4()
        uuid2 = uuid4()
        assert _update_item_upload(item_upload, upload_id=str(uuid1)).id == uuid1
        assert _update_item_upload(item_upload, upload_id=uuid2).id == uuid2

    def test_updates_path(self, item_upload: ItemUpload) -> None:
        assert _update_item_upload(item_upload, path=Path("/new/path")).path == Path("/new/path")

    def test_updates_item(self, item_upload: ItemUpload) -> None:
        item = ItemCore(
            name="file1.txt",
            id=uuid4(),
            slots=[],
            path="/path/to/file1.txt",
            dataset_id=1,
            processing_status="pending",
        )

        assert item_upload.item != item
        _update_item_upload(item_upload, item=item)
        assert item_upload.item == item


class TestItemDictToItem:
    IAD_RETURN_TYPE = Tuple[Item, Dict["str", UnknownType], Mock]

    @pytest.fixture
    def item_and_dict(self) -> IAD_RETURN_TYPE:
        client = MagicMock(spec=ClientCore)
        item_dict = {
            "name": "file1.txt",
            "id": "00000000-0000-0000-0000-000000000000",
            "slots": [],
            "path": "/path/to/file1.txt",
            "dataset_id": 1,
            "processing_status": "pending",
        }

        return Item(ItemCore.parse_obj(item_dict), client), item_dict, client

    def assert_optional_fields(
        self, item_property: Optional[UnknownType], item_dict_property: Optional[UnknownType]
    ) -> None:
        if not item_dict_property:
            return
        assert item_property == item_dict_property

    def compare_item_and_dict(self, item: Item, item_dict: Dict[str, UnknownType], client: ClientCore) -> None:
        item_element = item._element

        assert item_element.name == item_dict["name"]
        assert item_element.id == UUID(item_dict["id"])
        assert item_element.path == item_dict["path"]
        assert item_element.dataset_id == item_dict["dataset_id"]
        assert item_element.processing_status == item_dict["processing_status"]

        self.assert_optional_fields(item_element.archived, item_dict.get("archived"))
        self.assert_optional_fields(item_element.priority, item_dict.get("priority"))
        self.assert_optional_fields(item_element.tags, item_dict.get("tags"))
        self.assert_optional_fields(item_element.layout, item_dict.get("layout"))

        assert item.client == client

    def test_sets_all_required_fields(self, item_and_dict: IAD_RETURN_TYPE) -> None:
        _, item_dict, client = item_and_dict
        new_item = _item_dict_to_item(client, item_dict)

        self.compare_item_and_dict(new_item, item_dict, client)

    def test_sets_archived(self, item_and_dict: IAD_RETURN_TYPE) -> None:
        _, item_dict, client = item_and_dict
        item_dict["archived"] = True
        new_item = _item_dict_to_item(client, item_dict)

        self.compare_item_and_dict(new_item, item_dict, client)

    def test_sets_priority(self, item_and_dict: IAD_RETURN_TYPE) -> None:
        _, item_dict, client = item_and_dict
        item_dict["priority"] = 1
        new_item = _item_dict_to_item(client, item_dict)

        self.compare_item_and_dict(new_item, item_dict, client)

    def test_sets_tags(self, item_and_dict: IAD_RETURN_TYPE) -> None:
        _, item_dict, client = item_and_dict
        item_dict["tags"] = ["tag1", "tag2"]
        new_item = _item_dict_to_item(client, item_dict)

        self.compare_item_and_dict(new_item, item_dict, client)

    def test_sets_layout(self, item_and_dict: IAD_RETURN_TYPE) -> None:
        _, item_dict, client = item_and_dict
        item_dict["layout"] = ItemLayout(slots=["1"], type="grid", version=1, layout_shape=[1, 2, 3])
        new_item = _item_dict_to_item(client, item_dict)

        self.compare_item_and_dict(new_item, item_dict, client)


class TestItemsDictsToItems:
    def test_items_dicts_to_items(self) -> None:
        client = MagicMock(spec=ClientCore)
        item_dicts = [
            {
                "name": "file1.txt",
            },
            {
                "name": "file2.txt",
            },
            {
                "name": "file3.txt",
            },
        ]
        with patch("darwin.future.meta.meta_uploader._item_dict_to_item") as mock_item_dict_to_item:
            _items_dicts_to_items(client, item_dicts)

            mock_item_dict_to_item.assert_has_calls(
                [
                    call(client, item_dicts[0]),
                    call(client, item_dicts[1]),
                    call(client, item_dicts[2]),
                ]
            )


class TestInitialiseItemsAndBlockedItems:
    def test_calls_items_dicts_to_items_with_items(self):
        client = MagicMock(spec=ClientCore)
        item_dicts = [
            {
                "name": "file1.txt",
            },
            {
                "name": "file2.txt",
            },
            {
                "name": "file3.txt",
            },
        ]
        blocked_item_dicts = [
            {
                "name": "file4.txt",
            },
            {
                "name": "file5.txt",
            },
            {
                "name": "file6.txt",
            },
        ]
        with patch("darwin.future.meta.meta_uploader._items_dicts_to_items") as mock_items_dicts_to_items:
            _initialise_items_and_blocked_items(client, item_dicts, blocked_item_dicts)

            assert mock_items_dicts_to_items.call_args_list == [
                call(client, item_dicts),
                call(client, blocked_item_dicts),
            ]

    def test_raises_if_sub_function_raises(self):
        with patch("darwin.future.meta.meta_uploader._items_dicts_to_items") as mock_items_dicts_to_items:
            mock_items_dicts_to_items.side_effect = ValueError("test")
            with pytest.raises(ValueError) as exc:
                _initialise_items_and_blocked_items(MagicMock, [], [])
                assert exc.value.message == "test"  # type: ignore


class TestHandleUploads:
    @pytest.fixture
    def item_upload(self) -> ItemUpload:
        return ItemUpload(
            upload_item=UploadItem(
                name="file1.txt",
                path="/path/to/file1.txt",
                description="file1 description",
                tags=["tag1", "tag2"],
                layout=None,
                slots=[],
            ),
            status=ItemUploadStatus.PENDING,
        )

    @pytest.fixture
    def item_uploads(self) -> List[ItemUpload]:
        return [
            ItemUpload(
                upload_item=UploadItem(
                    name="file1.txt",
                    path="/path/to/file1.txt",
                    description="file1 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                status=ItemUploadStatus.PENDING,
            ),
            ItemUpload(
                upload_item=UploadItem(
                    name="file2.txt",
                    path="/path/to/file2.txt",
                    description="file2 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                status=ItemUploadStatus.PENDING,
            ),
            ItemUpload(
                upload_item=UploadItem(
                    name="file3.txt",
                    path="/path/to/file3.txt",
                    description="file3 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                status=ItemUploadStatus.PENDING,
            ),
        ]

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader._upload_file_to_signed_url")
    async def test_sets_status_to_uploading(self, item_uploads):
        await _handle_uploads(item_uploads)
        assert all(item_upload.status == ItemUploadStatus.UPLOADING for item_upload in item_uploads)

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader._upload_file_to_signed_url")
    async def test_raises_if_url_is_not_set(self, _, item_uploads: List[ItemUpload]):
        for item_upload in item_uploads:
            item_upload.url = None

        try:
            await _handle_uploads(item_uploads)
        except DarwinException as exc:
            assert exc.args[0] == "ItemUpload must have a path and url"
            # Below output will be FAILED, PENDING, PENDING because the first item will fail fast, halting the function
            assert item_uploads[0].status == ItemUploadStatus.FAILED
            assert all(item_upload.status == ItemUploadStatus.PENDING for item_upload in item_uploads[1:])
        else:
            pytest.fail("Expected ValueError for no url")

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader._upload_file_to_signed_url")
    async def test_raises_if_path_is_not_set(self, _, item_uploads: List[ItemUpload]):
        for item_upload in item_uploads:
            item_upload.url = None

        try:
            await _handle_uploads(item_uploads)
        except DarwinException as exc:
            assert exc.args[0] == "ItemUpload must have a path and url"
            # Below output will be FAILED, PENDING, PENDING because the first item will fail fast, halting the function
            assert item_uploads[0].status == ItemUploadStatus.FAILED
            assert all(item_upload.status == ItemUploadStatus.PENDING for item_upload in item_uploads[1:])
        else:
            pytest.fail("Expected ValueError for no url")

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader._upload_file_to_signed_url")
    async def test_raises_if_upload_fails(self, mock_upload_file_to_signed_url, item_uploads: List[ItemUpload]):
        mock_upload_file_to_signed_url.side_effect = DarwinException("test")

        with pytest.raises(DarwinException) as exc:
            await _handle_uploads(item_uploads)

            assert exc.value.message == "test"  # type: ignore

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader._upload_file_to_signed_url")
    async def test_happy_path(self, _, item_uploads: List[ItemUpload]):
        for item in item_uploads:
            item.url = "https://example.com"
            item.path = Path("/path/to/file.txt")

        await _handle_uploads(item_uploads)

        assert all(item_upload.status == ItemUploadStatus.UPLOADED for item_upload in item_uploads)


class TestConfirmUploads:
    @pytest.fixture
    def item_uploads(self) -> List[ItemUpload]:
        return [
            ItemUpload(
                upload_item=UploadItem(
                    name="file1.txt",
                    path="/path/to/file1.txt",
                    description="file1 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                status=ItemUploadStatus.PENDING,
            ),
            ItemUpload(
                upload_item=UploadItem(
                    name="file2.txt",
                    path="/path/to/file2.txt",
                    description="file2 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                status=ItemUploadStatus.PENDING,
            ),
            ItemUpload(
                upload_item=UploadItem(
                    name="file3.txt",
                    path="/path/to/file3.txt",
                    description="file3 description",
                    tags=["tag1", "tag2"],
                    layout=None,
                    slots=[],
                ),
                status=ItemUploadStatus.PENDING,
            ),
        ]

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader.asyncio.sleep")
    @patch("darwin.future.meta.meta_uploader.async_confirm_upload")
    async def test_runs_a_max_of_ten_times(self, mock_async_confirm_upload, _, item_uploads: List[ItemUpload]) -> None:
        mock_async_confirm_upload.side_effect = UploadPending("This is a test UploadPending")

        with pytest.raises(DarwinException) as exc:
            number_of_runs = 0
            while number_of_runs < 500:  # For safety
                try:
                    number_of_runs += 1
                    await _confirm_uploads(MagicMock(), "team_slug", item_uploads)
                except UploadPending:
                    continue
                else:
                    break

            assert exc.value.message == "Upload timed out"  # type: ignore
            assert number_of_runs == 10 * len(item_uploads)

            assert all(item_upload.status == ItemUploadStatus.PENDING for item_upload in item_uploads)

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader.asyncio.sleep")
    @patch("darwin.future.meta.meta_uploader.async_confirm_upload")
    async def test_does_not_call_api_when_status_is_already_not_pending(
        self, mock_async_confirm_upload, _, item_uploads
    ) -> None:
        new_item_uploads = item_uploads.copy()
        for item_upload in new_item_uploads:
            item_upload.status = ItemUploadStatus.UPLOADING

        await _confirm_uploads(MagicMock(), "team_slug", new_item_uploads)

        mock_async_confirm_upload.assert_not_called()

    @pytest.mark.asyncio
    @patch("darwin.future.meta.meta_uploader.asyncio.sleep")
    @patch("darwin.future.meta.meta_uploader.async_confirm_upload")
    async def test_sets_status_to_processing_if_no_longer_pending(
        self, mock_async_confirm_upload, _, item_uploads
    ) -> None:
        await _confirm_uploads(MagicMock(), "team_slug", item_uploads)

        assert all(item_upload.status == ItemUploadStatus.PROCESSING for item_upload in item_uploads)


class TestCombinedUploader:
    @contextmanager
    def patch_context(
        self,
        base_dataset: DatasetCore,
        mock_upload_items: List[UploadItem],
        upload_ids,
        upload_urls,
        item_dicts,
        blocked_item_dicts,
    ):
        def get_patch(name: str):
            return patch(f"darwin.future.meta.meta_uploader.{name}")

        with get_patch("get_dataset") as mock_get_dataset, get_patch(
            "_create_list_of_all_files"
        ) as mock_create_list_of_all_files, get_patch("_derive_root_path") as mock_derive_root_path, get_patch(
            "_prepare_upload_items"
        ) as mock_prepare_upload_items, get_patch(
            "_initialise_item_uploads"
        ) as mock_initialise_item_uploads, get_patch(
            "_initialise_items_and_paths"
        ) as mock_initialise_items_and_paths, get_patch(
            "async_register_and_create_signed_upload_url"
        ) as mock_async_register_and_create_signed_upload_url, get_patch(
            "_handle_uploads"
        ) as mock__handle_uploads, get_patch(
            "_confirm_uploads"
        ) as mock_confirm_uploads:
            mock_get_dataset.return_value = base_dataset
            mock_create_list_of_all_files.return_value = [Path("/path/to/file1.jpg"), Path("/path/to/file2.jpg")]
            mock_derive_root_path.return_value = Path("/"), Path("/")
            mock_prepare_upload_items.return_value = mock_upload_items
            mock_initialise_item_uploads.return_value = [
                ItemUpload(upload_item=upload_item, status=ItemUploadStatus.PENDING)
                for upload_item in mock_upload_items
            ]
            mock_initialise_items_and_paths.return_value = [
                (upload_item, Path("/")) for upload_item in mock_upload_items
            ]
            mock_async_register_and_create_signed_upload_url.return_value = (
                upload_ids,
                upload_urls,
                item_dicts,
                blocked_item_dicts,
            )
            mock__handle_uploads.return_value = None
            mock_confirm_uploads.return_value = None

            yield (
                mock_get_dataset,
                mock_create_list_of_all_files,
                mock_derive_root_path,
                mock_prepare_upload_items,
                mock_initialise_item_uploads,
                mock_initialise_items_and_paths,
                mock_async_register_and_create_signed_upload_url,
                mock__handle_uploads,
                mock_confirm_uploads,
            )

    @pytest.fixture
    def item_create(self) -> ItemCreate:
        return ItemCreate(
            files=[Path("/path/to/file1.jpg"), Path("/path/to/file2.jpg")],
            callback_when_complete=MagicMock(),
            callback_when_loaded=MagicMock(),
            callback_when_loading=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_happy_path(
        self,
        base_dataset: DatasetCore,
        mock_upload_items: List[UploadItem],
        upload_ids,
        upload_urls,
        item_dicts,
        blocked_item_dicts,
        item_create,
    ):
        with self.patch_context(
            base_dataset, mock_upload_items, upload_ids, upload_urls, item_dicts, blocked_item_dicts
        ) as (
            mock_get_dataset,
            mock_create_list_of_all_files,
            mock_derive_root_path,
            mock_prepare_upload_items,
            mock_initialise_item_uploads,
            mock_initialise_items_and_paths,
            mock_async_register_and_create_signed_upload_url,
            mock__handle_uploads,
            mock_confirm_uploads,
        ):
            client = MagicMock()

            await combined_uploader(client, "team_slug", 1, item_create)

    @pytest.mark.asyncio
    async def test_raises_if_functions_raise(
        self,
        base_dataset: DatasetCore,
        mock_upload_items: List[UploadItem],
        upload_ids,
        upload_urls,
        item_dicts,
        blocked_item_dicts,
        item_create,
    ):
        with self.patch_context(
            base_dataset, mock_upload_items, upload_ids, upload_urls, item_dicts, blocked_item_dicts
        ) as (
            mock_get_dataset,
            mock_create_list_of_all_files,
            mock_derive_root_path,
            mock_prepare_upload_items,
            mock_initialise_item_uploads,
            mock_initialise_items_and_paths,
            mock_async_register_and_create_signed_upload_url,
            mock__handle_uploads,
            mock_confirm_uploads,
        ):
            client = MagicMock()
            mocks = [
                mock_get_dataset,
                mock_create_list_of_all_files,
                mock_derive_root_path,
                mock_prepare_upload_items,
                mock_initialise_item_uploads,
                mock_initialise_items_and_paths,
                mock_async_register_and_create_signed_upload_url,
                mock__handle_uploads,
                mock_confirm_uploads,
            ]
            for mock in mocks:
                mock.side_effect = DarwinException("test")
            with pytest.raises(DarwinException) as exc:
                await combined_uploader(client, "team_slug", 1, item_create)
                assert exc.value.message == "test"  # type: ignore
