import types
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import orjson as json
import pytest
import responses

from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.release import Release
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.dataset.upload_manager import LocalFile, UploadHandlerV2
from darwin.exceptions import UnsupportedExportFormat, UnsupportedFileType
from darwin.item import DatasetItem
from tests.fixtures import *


@pytest.fixture
def annotation_name() -> str:
    return "test_video.json"


@pytest.fixture
def annotation_content() -> Dict[str, Any]:
    return {
        "image": {
            "width": 1920,
            "height": 1080,
            "filename": "test_video.mp4",
            "fps": 20.0,
            "frame_urls": ["frame_1.jpg", "frame_2.jpg", "frame_3.jpg"],
        },
        "annotations": [
            {
                "frames": {
                    "0": {
                        "polygon": {
                            "path": [
                                {"x": 0, "y": 0},
                                {"x": 1, "y": 1},
                                {"x": 1, "y": 0},
                            ]
                        }
                    },
                    "2": {
                        "polygon": {
                            "path": [
                                {"x": 5, "y": 5},
                                {"x": 6, "y": 6},
                                {"x": 6, "y": 5},
                            ]
                        }
                    },
                    "4": {
                        "polygon": {
                            "path": [
                                {"x": 9, "y": 9},
                                {"x": 8, "y": 8},
                                {"x": 8, "y": 9},
                            ]
                        }
                    },
                },
                "name": "test_class",
                "segments": [[0, 3]],
            }
        ],
    }


@pytest.fixture
def darwin_client(
    darwin_config_path: Path,
    darwin_datasets_path: Path,
    team_slug_darwin_json_v2: str,
) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug_darwin_json_v2, "api_key"], "mock_api_key")
    config.put(
        ["teams", team_slug_darwin_json_v2, "datasets_dir"], str(darwin_datasets_path)
    )
    return Client(config)


@pytest.fixture
def create_annotation_file(
    darwin_datasets_path: Path,
    team_slug_darwin_json_v2: str,
    dataset_slug: str,
    release_name: str,
    annotation_name: str,
    annotation_content: dict,
):
    annotations: Path = (
        darwin_datasets_path
        / team_slug_darwin_json_v2
        / dataset_slug
        / "releases"
        / release_name
        / "annotations"
    )
    annotations.mkdir(exist_ok=True, parents=True)

    with (annotations / annotation_name).open("w") as f:
        op = json.dumps(annotation_content).decode("utf-8")
        f.write(op)


@pytest.fixture()
def files_content() -> Dict[str, Any]:
    return {
        "items": [
            {
                "id": "018c6826-766c-d596-44b3-46159c7c23bc",
                "name": "segment_1.mp4",
                "priority": 0,
                "status": "new",
                "path": "/",
                "tags": [],
                "cursor": "018c6826-766c-d596-44b3-46159c7c23bc",
                "layout": {"type": "simple", "version": 1, "slots": ["0"]},
                "uploads": [],
                "slots": [
                    {
                        "id": "daf0b44e-b328-4d6b-8148-e7f348cd16f5",
                        "type": "video",
                        "metadata": {
                            "height": 1920,
                            "native_fps": 30,
                            "segment_index": [
                                "#EXTM3U",
                                "#EXT-X-VERSION:3",
                                "#EXT-X-TARGETDURATION:11",
                                "#EXT-X-MEDIA-SEQUENCE:0",
                                "#EXTINF:11.500000,",
                                "data/teams/3961/partition_53/018c6826-766c-d596-44b3-46159c7c23bc/uploads/dc647e0e-917f-4586-8b51-2ebc37613884.mp4/segments/000000000.ts",
                                "#EXT-X-ENDLIST",
                                "",
                            ],
                            "width": 1080,
                        },
                        "file_name": "segment_1.mp4",
                        "fps": 0.58,
                        "slot_name": "0",
                        "total_sections": 7,
                        "sectionless": False,
                        "upload_id": "dc647e0e-917f-4586-8b51-2ebc37613884",
                        "size_bytes": 12220902,
                        "is_external": False,
                        "streamable": True,
                    }
                ],
                "inserted_at": "2023-12-14T11:46:40Z",
                "updated_at": "2023-12-14T11:46:40Z",
                "dataset_id": 611387,
                "archived": False,
                "processing_status": "complete",
                "workflow_status": "new",
                "slot_types": ["video"],
            },
            {
                "id": "018cf7e3-a43d-8d2b-cc04-375004360f51",
                "name": "hang_-_30902 (540p).mp4",
                "priority": 0,
                "status": "new",
                "path": "/",
                "tags": [],
                "cursor": "018cf7e3-a43d-8d2b-cc04-375004360f51",
                "layout": {"type": "simple", "version": 1, "slots": ["0"]},
                "uploads": [],
                "slots": [
                    {
                        "id": "8d8ebdd0-e405-4ff4-9899-ecc91f39322c",
                        "type": "video",
                        "metadata": {
                            "frames_manifests": [
                                {
                                    "total_frames": 611,
                                    "url": "https://darwin.v7labs.com/s/data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/frames_manifest.txt?token=SFMyNTY.eyJleHAiOjE3MDcwNjkxOTcsImtleV9wcmVmaXgiOiJkYXRhL3RlYW1zLzM5NjEvcGFydGl0aW9uXzUzLzAxOGNmN2UzLWE0M2QtOGQyYi1jYzA0LTM3NTAwNDM2MGY1MS8ifQ.A5lUGz5VFnzEs6NUi4vYw9mw17kqGSzu0FVoBBt1oXE",
                                    "visible_frames": 25,
                                }
                            ],
                            "height": 540,
                            "native_fps": 25,
                            "segment_index": [
                                "#EXTM3U",
                                "#EXT-X-VERSION:3",
                                "#EXT-X-TARGETDURATION:3",
                                "#EXT-X-MEDIA-SEQUENCE:0",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000000.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000001.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000002.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000003.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000004.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000005.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000006.ts",
                                "#EXTINF:3.040000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000007.ts",
                                "#EXTINF:0.120000,",
                                "data/teams/3961/partition_53/018cf7e3-a43d-8d2b-cc04-375004360f51/uploads/fc994bd0-61a7-4c1f-b9d2-0715b3c51e13.mp4/segments/000000008.ts",
                                "#EXT-X-ENDLIST",
                                "",
                            ],
                            "width": 960,
                        },
                        "file_name": "hang_-_30902 (540p).mp4",
                        "fps": 1,
                        "slot_name": "0",
                        "total_sections": 25,
                        "sectionless": True,
                        "upload_id": "fc994bd0-61a7-4c1f-b9d2-0715b3c51e13",
                        "size_bytes": 5754208,
                        "is_external": False,
                        "streamable": True,
                    }
                ],
                "inserted_at": "2024-01-11T09:39:00Z",
                "updated_at": "2024-01-25T23:05:35.454727Z",
                "dataset_id": 611387,
                "archived": False,
                "processing_status": "complete",
                "workflow_status": "new",
                "slot_types": ["video"],
            },
        ],
        "page": {
            "count": 2,
            "next": None,
            "previous": "018c6826-766c-d596-44b3-46159c7c23bc",
        },
    }


# This test was never actually running
# TODO: Fix this test
# class TestDatasetCreation:
#     def test_should_set_id_correctly_from_id(self, darwin_client: Client):
#         dataset_id = "team_slug/dataset_name:test_release"
#         dataset = darwin_client.get_remote_dataset(dataset_id)

#         assert dataset.slug == "team_slug"
#         assert dataset.name == "dataset_name"
#         assert dataset.release == "test_release"

#     def test_should_work_without_a_release(self, darwin_client: Client):
#         dataset_id = "team_slug/dataset_name"
#         dataset = darwin_client.get_remote_dataset(dataset_id)

#         assert dataset.slug == "team_slug"
#         assert dataset.name == "dataset_name"
#         assert dataset.release == None


@pytest.mark.usefixtures("file_read_write_test", "create_annotation_file")
class TestSplitVideoAnnotations:
    def test_works_on_videos(
        self,
        darwin_client: Client,
        darwin_datasets_path: Path,
        dataset_name: str,
        dataset_slug: str,
        release_name: str,
        team_slug_darwin_json_v2: str,
    ):
        remote_dataset = RemoteDatasetV2(
            client=darwin_client,
            team=team_slug_darwin_json_v2,
            name=dataset_name,
            slug=dataset_slug,
            dataset_id=1,
        )

        remote_dataset.split_video_annotations()

        video_path = (
            darwin_datasets_path
            / team_slug_darwin_json_v2
            / dataset_slug
            / "releases"
            / release_name
            / "annotations"
            / "test_video"
        )
        assert video_path.exists()
        assert (video_path / "0000000.json").exists()
        assert (video_path / "0000001.json").exists()
        assert (video_path / "0000002.json").exists()
        assert not (video_path / "0000003.json").exists()

        with (video_path / "0000000.json").open() as f:
            assert json.loads(f.read()) == {
                "annotations": [
                    {
                        "name": "test_class",
                        "polygon": {
                            "path": [
                                {"x": 0, "y": 0},
                                {"x": 1, "y": 1},
                                {"x": 1, "y": 0},
                            ]
                        },
                    }
                ],
                "image": {
                    "filename": "test_video/0000000.png",
                    "height": 1080,
                    "url": "frame_1.jpg",
                    "width": 1920,
                },
            }

        with (video_path / "0000001.json").open() as f:
            assert json.loads(f.read()) == {
                "annotations": [],
                "image": {
                    "filename": "test_video/0000001.png",
                    "height": 1080,
                    "url": "frame_2.jpg",
                    "width": 1920,
                },
            }

        with (video_path / "0000002.json").open() as f:
            assert json.loads(f.read()) == {
                "annotations": [
                    {
                        "name": "test_class",
                        "polygon": {
                            "path": [
                                {"x": 5, "y": 5},
                                {"x": 6, "y": 6},
                                {"x": 6, "y": 5},
                            ]
                        },
                    }
                ],
                "image": {
                    "filename": "test_video/0000002.png",
                    "height": 1080,
                    "url": "frame_3.jpg",
                    "width": 1920,
                },
            }


@pytest.mark.usefixtures("files_content", "file_read_write_test")
class TestFetchRemoteFiles:
    @responses.activate
    def test_works(
        self,
        darwin_client: Client,
        dataset_name: str,
        dataset_slug: str,
        team_slug_darwin_json_v2: str,
        files_content: dict,
    ):
        remote_dataset = RemoteDatasetV2(
            client=darwin_client,
            team=team_slug_darwin_json_v2,
            name=dataset_name,
            slug=dataset_slug,
            dataset_id=1,
        )
        url = "http://localhost/api/v2/teams/v7-darwin-json-v2/items?page%5Bsize%5D=500&include_workflow_data=true&dataset_ids%5B%5D=1"
        responses.add(
            responses.GET,
            url,
            json=files_content,
            status=200,
        )

        actual = remote_dataset.fetch_remote_files()

        assert isinstance(actual, types.GeneratorType)

        (item_1, item_2) = list(actual)

        assert responses.assert_call_count(url, 1) is True

        assert item_1.id == "018c6826-766c-d596-44b3-46159c7c23bc"
        assert item_2.id == "018cf7e3-a43d-8d2b-cc04-375004360f51"

    @responses.activate
    def test_fetches_files_with_commas(
        self,
        darwin_client: Client,
        dataset_name: str,
        dataset_slug: str,
        team_slug_darwin_json_v2: str,
        files_content: dict,
    ):
        remote_dataset = RemoteDatasetV2(
            client=darwin_client,
            team=team_slug_darwin_json_v2,
            name=dataset_name,
            slug=dataset_slug,
            dataset_id=1,
        )
        url = "http://localhost/api/v2/teams/v7-darwin-json-v2/items?item_names%5B%5D=example%2Cwith%2C+comma.mp4&page%5Bsize%5D=500&include_workflow_data=true&dataset_ids%5B%5D=1"
        responses.add(
            responses.GET,
            url,
            json=files_content,
            status=200,
        )

        list(
            remote_dataset.fetch_remote_files(
                {"item_names": ["example,with, comma.mp4"]}
            )
        )

        request_body = json.loads(responses.calls[0].request.body)

        assert request_body["filter"]["filenames"] == ["example,with, comma.mp4"]


@pytest.fixture
def remote_dataset(
    darwin_client: Client,
    dataset_name: str,
    dataset_slug: str,
    team_slug_darwin_json_v2: str,
):
    return RemoteDatasetV2(
        client=darwin_client,
        team=team_slug_darwin_json_v2,
        name=dataset_name,
        slug=dataset_slug,
        dataset_id=1,
    )


@pytest.mark.usefixtures("file_read_write_test")
class TestPush:
    def test_raises_if_files_are_not_provided(self, remote_dataset: RemoteDataset):
        with pytest.raises(ValueError):
            remote_dataset.push(None)

    def test_raises_if_both_path_and_local_files_are_given(
        self, remote_dataset: RemoteDataset
    ):
        with pytest.raises(ValueError):
            remote_dataset.push([LocalFile("test.jpg")], path="test")

    def test_raises_if_both_fps_and_local_files_are_given(
        self, remote_dataset: RemoteDataset
    ):
        with pytest.raises(ValueError):
            remote_dataset.push([LocalFile("test.jpg")], fps=2)

    def test_raises_if_both_as_frames_and_local_files_are_given(
        self, remote_dataset: RemoteDataset
    ):
        with pytest.raises(ValueError):
            remote_dataset.push([LocalFile("test.jpg")], as_frames=True)

    def test_works_with_local_files_list(self, remote_dataset: RemoteDataset):
        assert_upload_mocks_are_correctly_called(
            remote_dataset, [LocalFile("test.jpg")]
        )

    def test_works_with_path_list(self, remote_dataset: RemoteDataset):
        assert_upload_mocks_are_correctly_called(remote_dataset, [Path("test.jpg")])

    def test_works_with_str_list(self, remote_dataset: RemoteDataset):
        assert_upload_mocks_are_correctly_called(remote_dataset, ["test.jpg"])

    def test_works_with_supported_files(self, remote_dataset: RemoteDataset):
        supported_extensions = [
            ".png",
            ".jpeg",
            ".jpg",
            ".jfif",
            ".tif",
            ".tiff",
            ".bmp",
            ".svs",
            ".avi",
            ".bpm",
            ".dcm",
            ".mov",
            ".mp4",
            ".pdf",
            ".ndpi",
        ]
        filenames = [f"test{extension}" for extension in supported_extensions]
        assert_upload_mocks_are_correctly_called(remote_dataset, filenames)

    def test_raises_with_unsupported_files(self, remote_dataset: RemoteDataset):
        with pytest.raises(UnsupportedFileType):
            remote_dataset.push(["test.txt"])


@pytest.mark.usefixtures("file_read_write_test")
class TestPull:
    @patch("platform.system", return_value="Linux")
    def test_gets_latest_release_when_not_given_one(
        self, system_mock: MagicMock, remote_dataset: RemoteDataset
    ):
        stub_release_response = Release(
            "dataset-slug",
            "team-slug",
            "0.1.0",
            "release-name",
            "http://darwin-fake-url.com",
            datetime.now(),
            None,
            None,
            True,
            True,
            "json",
        )

        def fake_download_zip(self, path):
            zip: Path = Path("tests/dataset.zip")
            shutil.copy(zip, path)
            return path

        with patch.object(
            RemoteDataset, "get_release", return_value=stub_release_response
        ) as get_release_stub:
            with patch.object(Release, "download_zip", new=fake_download_zip):
                remote_dataset.pull(only_annotations=True)
                get_release_stub.assert_called_once()

    @patch("platform.system", return_value="Windows")
    def test_does_not_create_symlink_on_windows(
        self, mocker: MagicMock, remote_dataset: RemoteDataset
    ):
        stub_release_response = Release(
            "dataset-slug",
            "team-slug",
            "0.1.0",
            "release-name",
            "http://darwin-fake-url.com",
            datetime.now(),
            None,
            None,
            True,
            True,
            "json",
        )

        def fake_download_zip(self, path):
            zip: Path = Path("tests/dataset.zip")
            shutil.copy(zip, path)
            return path

        latest: Path = remote_dataset.local_releases_path / "latest"

        with patch.object(
            RemoteDataset, "get_release", return_value=stub_release_response
        ):
            with patch.object(Release, "download_zip", new=fake_download_zip):
                remote_dataset.pull(only_annotations=True)
                assert not latest.is_symlink()

    @patch("platform.system", return_value="Linux")
    def test_continues_if_symlink_creation_fails(
        self, system_mock: MagicMock, remote_dataset: RemoteDataset
    ):
        stub_release_response = Release(
            "dataset-slug",
            "team-slug",
            "0.1.0",
            "release-name",
            "http://darwin-fake-url.com",
            datetime.now(),
            None,
            None,
            True,
            True,
            "json",
        )

        def fake_download_zip(self, path):
            zip: Path = Path("tests/dataset.zip")
            shutil.copy(zip, path)
            return path

        latest: Path = remote_dataset.local_releases_path / "latest"

        with patch.object(Path, "symlink_to") as mock_symlink_to:
            with patch.object(
                RemoteDataset, "get_release", return_value=stub_release_response
            ):
                with patch.object(Release, "download_zip", new=fake_download_zip):
                    mock_symlink_to.side_effect = OSError()
                    remote_dataset.pull(only_annotations=True)
                    assert not latest.is_symlink()

    @patch("platform.system", return_value="Linux")
    def test_raises_if_release_format_is_not_json(
        self, system_mock: MagicMock, remote_dataset: RemoteDataset
    ):
        a_release = Release(
            remote_dataset.slug,
            remote_dataset.team,
            "0.1.0",
            "release-name",
            "http://darwin-fake-url.com",
            datetime.now(),
            None,
            None,
            True,
            True,
            "xml",
        )

        with pytest.raises(UnsupportedExportFormat):
            remote_dataset.pull(release=a_release)


@pytest.fixture
def dataset_item(dataset_slug: str) -> DatasetItem:
    return DatasetItem(
        id=1,
        filename="test.jpg",
        status="new",
        archived=False,
        filesize=1,
        dataset_id=1,
        dataset_slug=dataset_slug,
        seq=1,
        current_workflow_id=None,
        current_workflow=None,
        path="/",
        slots=[],
    )


@pytest.mark.usefixtures("file_read_write_test")
class TestArchive:
    def test_calls_put(
        self,
        remote_dataset: RemoteDatasetV2,
        dataset_item: DatasetItem,
        team_slug_darwin_json_v2: str,
        dataset_slug: str,
    ):
        with patch.object(RemoteDatasetV2, "archive", return_value={}) as stub:
            remote_dataset.archive([dataset_item])
            stub.assert_called_once_with([dataset_item])


@pytest.mark.usefixtures("file_read_write_test")
class TestMoveToNew:
    def test_calls_put(
        self,
        remote_dataset: RemoteDatasetV2,
        dataset_item: DatasetItem,
        team_slug_darwin_json_v2: str,
        dataset_slug: str,
    ):
        with patch.object(RemoteDatasetV2, "move_to_new", return_value={}) as stub:
            remote_dataset.move_to_new([dataset_item])
            stub.assert_called_once_with([dataset_item])


@pytest.mark.usefixtures("file_read_write_test")
class TestRestoreArchived:
    def test_calls_put(
        self,
        remote_dataset: RemoteDatasetV2,
        dataset_item: DatasetItem,
        team_slug_darwin_json_v2: str,
        dataset_slug: str,
    ):
        with patch.object(RemoteDatasetV2, "restore_archived", return_value={}) as stub:
            remote_dataset.restore_archived([dataset_item])
            stub.assert_called_once_with([dataset_item])


@pytest.mark.usefixtures("file_read_write_test")
class TestDeleteItems:
    def test_calls_delete(
        self,
        remote_dataset: RemoteDatasetV2,
        dataset_item: DatasetItem,
        team_slug_darwin_json_v2: str,
        dataset_slug: str,
    ):
        with patch.object(RemoteDatasetV2, "delete_items", return_value={}) as stub:
            remote_dataset.delete_items([dataset_item])
            stub.assert_called_once_with([dataset_item])


def assert_upload_mocks_are_correctly_called(remote_dataset: RemoteDataset, *args):
    with patch.object(
        UploadHandlerV2, "_request_upload", return_value=([], [])
    ) as request_upload_mock:
        with patch.object(UploadHandlerV2, "upload") as upload_mock:
            remote_dataset.push(*args)

            request_upload_mock.assert_called_once()
            upload_mock.assert_called_once_with(
                multi_threaded=True,
                progress_callback=None,
                file_upload_callback=None,
                max_workers=None,
            )


@pytest.mark.usefixtures("file_read_write_test")
class TestExportDataset:
    def test_honours_include_authorship(self, remote_dataset: RemoteDatasetV2):
        with patch.object(RemoteDatasetV2, "export", return_value={}) as stub:
            remote_dataset.export(
                "example",
                annotation_class_ids=[],
                include_url_token=False,
                include_authorship=True,
            )
            stub.assert_called_once_with(
                "example",
                annotation_class_ids=[],
                include_url_token=False,
                include_authorship=True,
            )
