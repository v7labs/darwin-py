from pathlib import Path

from unittest.mock import PropertyMock, patch

from darwin.cli_functions import _load_client
from darwin.dataset import RemoteDataset


def glob():
    filenames = ["one.json", "two.json", "three.json"]
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


@patch("darwin.dataset.RemoteDataset.local_path", new_callable=PropertyMock, return_value=Path("test"))
@patch("json.load", return_value=parsed_image_annotation_file())
@patch("pathlib.Path.exists", return_value=True)
@patch("pathlib.Path.glob", return_value=glob())
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.open")
def test_split_video_annotations_on_images(*mocks):
    client = _load_client(offline=True)
    remote_dataset = RemoteDataset(client=client, team="v7", name="test_dataset", slug="test-dataset", dataset_id=1)

    remote_dataset.split_video_annotations()

    for mock in mocks:
        mock.assert_called()


@patch("darwin.dataset.RemoteDataset.local_path", new_callable=PropertyMock, return_value=Path("test"))
@patch("json.dump")
@patch("json.load", return_value=parsed_video_annotation_file())
@patch("pathlib.Path.exists", return_value=True)
@patch("pathlib.Path.glob", return_value=glob())
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.open")
@patch("pathlib.Path.unlink")
def test_split_video_annotations_on_videos(*mocks):
    client = _load_client(offline=True)
    remote_dataset = RemoteDataset(client=client, team="v7", name="test_dataset", slug="test-dataset", dataset_id=1)

    remote_dataset.split_video_annotations()

    for mock in mocks:
        mock_name = mock._extract_mock_name()
        # 3 frames for each one of the 3 video annotations are loaded
        if mock_name == "dump":
            assert mock.call_count == 9
        # 3 video annotations are loaded
        elif mock_name == "load":
            assert mock.call_count == 3
        mock.assert_called()
