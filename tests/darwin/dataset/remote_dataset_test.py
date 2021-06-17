from pathlib import Path

from unittest.mock import patch

from darwin.cli_functions import _load_client
from darwin.dataset import RemoteDataset


def glob():
    filenames = ["frame_1.json", "frame_2.json", "frame_3.json"]
    return map(Path, filenames)


def parsed_image_annotation_file():
    return {"image": {"width": 1920, "height": 1080, "filename": "test.jpg"}, "annotations": []}


def parsed_video_annotation_file():
    return {
        "image": {
            "width": 1920,
            "height": 1080,
            "filename": "test.mp4",
            "fps": 20.0,
            "frame_urls": ["frame_1.jpg", "frame_2.jpg", "frame_3.jpg"],
        },
        "annotations": [],
    }


@patch("json.load", return_value=parsed_image_annotation_file())
@patch("pathlib.Path.exists", return_value=True)
@patch("pathlib.Path.glob", return_value=glob())
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.open")
def test_split_video_annotations_on_images(
    json_load_mock, path_exists_mock, path_glob_mock, path_mkdir_mock, path_open_mock
):
    client = _load_client(offline=True)
    remote_dataset = RemoteDataset(client=client, team="v7", name="test_dataset", slug="test-dataset", dataset_id=1)

    remote_dataset.split_video_annotations()

    json_load_mock.assert_called()
    path_exists_mock.assert_called()
    path_glob_mock.assert_called()
    path_mkdir_mock.assert_called()
    path_open_mock.assert_called()


@patch("json.dump")
@patch("json.load", return_value=parsed_video_annotation_file())
@patch("pathlib.Path.exists", return_value=True)
@patch("pathlib.Path.glob", return_value=glob())
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.open")
@patch("pathlib.Path.unlink")
def test_split_video_annotations_on_videos(
    json_dump_mock, json_load_mock, path_exists_mock, path_glob_mock, path_mkdir_mock, path_open_mock, path_unlink_mock
):
    client = _load_client(offline=True)
    remote_dataset = RemoteDataset(client=client, team="v7", name="test_dataset", slug="test-dataset", dataset_id=1)

    remote_dataset.split_video_annotations()

    # json.dump() is called once per frame
    assert json_dump_mock.call_count == 3

    json_load_mock.assert_called()
    path_exists_mock.assert_called()
    path_glob_mock.assert_called()
    path_mkdir_mock.assert_called()
    path_open_mock.assert_called()
    path_unlink_mock.assert_called()
