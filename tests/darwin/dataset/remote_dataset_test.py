import json
from unittest.mock import patch

import pytest
from darwin.client import Client
from darwin.config import Config
from darwin.dataset import RemoteDataset
from darwin.dataset.upload_manager import LocalFile, UploadHandler
from tests.fixtures import *


@pytest.fixture
def annotation_name() -> str:
    return "test_video.json"


@pytest.fixture
def annotation_content() -> dict:
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
                    "0": {"polygon": {"path": [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 1, "y": 0}]}},
                    "2": {"polygon": {"path": [{"x": 5, "y": 5}, {"x": 6, "y": 6}, {"x": 6, "y": 5}]}},
                    "4": {"polygon": {"path": [{"x": 9, "y": 9}, {"x": 8, "y": 8}, {"x": 8, "y": 9}]}},
                },
                "name": "test_class",
                "segments": [[0, 3]],
            }
        ],
    }


@pytest.fixture
def darwin_client(darwin_config_path: Path, darwin_datasets_path: Path, team_slug: str) -> Client:
    config = Config(darwin_config_path)
    config.put(["teams", team_slug, "api_key"], "mock_api_key")
    config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
    return Client(config)


@pytest.fixture
def create_annotation_file(
    darwin_datasets_path: Path,
    team_slug: str,
    dataset_slug: str,
    release_name: str,
    annotation_name: str,
    annotation_content: dict,
):
    annotations_path = darwin_datasets_path / team_slug / dataset_slug / "releases" / release_name / "annotations"
    annotations_path.mkdir(exist_ok=True, parents=True)

    with (annotations_path / annotation_name).open("w") as f:
        json.dump(annotation_content, f)


@pytest.mark.usefixtures("file_read_write_test", "create_annotation_file")
def test_split_video_annotations_on_videos(
    darwin_client: Client,
    darwin_datasets_path: Path,
    dataset_name: str,
    dataset_slug: str,
    release_name: str,
    team_slug: str,
):
    remote_dataset = RemoteDataset(
        client=darwin_client, team=team_slug, name=dataset_name, slug=dataset_slug, dataset_id=1
    )

    remote_dataset.split_video_annotations()

    video_path = (
        darwin_datasets_path / team_slug / dataset_slug / "releases" / release_name / "annotations" / "test_video"
    )
    assert video_path.exists()

    assert (video_path / "0000000.json").exists()
    assert (video_path / "0000001.json").exists()
    assert (video_path / "0000002.json").exists()
    assert not (video_path / "0000003.json").exists()

    with (video_path / "0000000.json").open() as f:
        assert json.load(f) == {
            "annotations": [
                {"name": "test_class", "polygon": {"path": [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 1, "y": 0}]}}
            ],
            "image": {"filename": "test_video/0000000.jpg", "height": 1080, "url": "frame_1.jpg", "width": 1920},
        }

    with (video_path / "0000001.json").open() as f:
        assert json.load(f) == {
            "annotations": [],
            "image": {"filename": "test_video/0000001.jpg", "height": 1080, "url": "frame_2.jpg", "width": 1920},
        }

    with (video_path / "0000002.json").open() as f:
        assert json.load(f) == {
            "annotations": [
                {"name": "test_class", "polygon": {"path": [{"x": 5, "y": 5}, {"x": 6, "y": 6}, {"x": 6, "y": 5}]}}
            ],
            "image": {"filename": "test_video/0000002.jpg", "height": 1080, "url": "frame_3.jpg", "width": 1920},
        }


@pytest.mark.usefixtures("file_read_write_test")
def describe_push():
    @pytest.fixture
    def remote_dataset(darwin_client: Client, dataset_name: str, dataset_slug: str, team_slug: str):
        return RemoteDataset(client=darwin_client, team=team_slug, name=dataset_name, slug=dataset_slug, dataset_id=1)

    def raises_if_files_are_not_provided(remote_dataset: RemoteDataset):
        with pytest.raises(ValueError):
            remote_dataset.push(None)

    def raises_if_both_path_and_local_files_are_given(remote_dataset: RemoteDataset):
        with pytest.raises(ValueError):
            remote_dataset.push([LocalFile("test.jpg")], path="test")

    def raises_if_both_fps_and_local_files_are_given(remote_dataset: RemoteDataset):
        with pytest.raises(ValueError):
            remote_dataset.push([LocalFile("test.jpg")], fps=2)

    def raises_if_both_as_frames_and_local_files_are_given(remote_dataset: RemoteDataset):
        with pytest.raises(ValueError):
            remote_dataset.push([LocalFile("test.jpg")], as_frames=True)

    def works_with_local_files_list(remote_dataset: RemoteDataset):
        assert_upload_mocks_are_correctly_called(remote_dataset, [LocalFile("test.jpg")])

    def works_with_path_list(remote_dataset: RemoteDataset):
        assert_upload_mocks_are_correctly_called(remote_dataset, [Path("test.jpg")])

    def works_with_str_list(remote_dataset: RemoteDataset):
        assert_upload_mocks_are_correctly_called(remote_dataset, ["test.jpg"])


def assert_upload_mocks_are_correctly_called(remote_dataset: RemoteDataset, *args):
    with patch.object(UploadHandler, "_request_upload", return_value=([], [])) as request_upload_mock:
        with patch.object(UploadHandler, "upload") as upload_mock:
            remote_dataset.push(*args)

            request_upload_mock.assert_called_once()
            upload_mock.assert_called_once_with(multi_threaded=True, progress_callback=None, file_upload_callback=None)
