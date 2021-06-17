import json

import pytest
from unittest.mock import PropertyMock, patch

from darwin.cli_functions import _load_client
from darwin.dataset import RemoteDataset
from tests.utils import *


def image_annotation_file_content():
    return {
        "image": {"width": 1920, "height": 1080, "filename": "test_image.jpg"},
        "annotations": [
            {"name": "test_class_1", "polygon": {"path": [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 1, "y": 0}]}},
            {"name": "test_class_2", "polygon": {"path": [{"x": 5, "y": 5}, {"x": 6, "y": 6}, {"x": 6, "y": 5}]}},
            {"name": "test_class_3", "polygon": {"path": [{"x": 9, "y": 9}, {"x": 8, "y": 8}, {"x": 8, "y": 9}]}},
        ],
    }


def video_annotation_file_content():
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


@patch(
    "darwin.dataset.RemoteDataset.local_path",
    new_callable=PropertyMock,
    return_value=DARWIN_TEST_PATH / DARWIN_TEAM_NAME / DARWIN_DATASET_NAME,
)
@pytest.mark.usefixtures("file_read_write_test")
def test_split_video_annotations_on_images(*mocks):
    setup_darwin_test_path(team_name=DARWIN_TEAM_NAME, dataset_name=DARWIN_DATASET_NAME)

    create_annotation_file(
        name="image.json",
        content=image_annotation_file_content(),
        team_name=DARWIN_TEAM_NAME,
        dataset_name=DARWIN_DATASET_NAME,
    )

    client = _load_client(offline=True)
    remote_dataset = RemoteDataset(
        client=client, team=DARWIN_TEAM_NAME, name=DARWIN_DATASET_NAME, slug="test-dataset", dataset_id=1
    )

    remote_dataset.split_video_annotations()

    for mock in mocks:
        mock.assert_called()


@patch(
    "darwin.dataset.RemoteDataset.local_path",
    new_callable=PropertyMock,
    return_value=DARWIN_TEST_PATH / DARWIN_TEAM_NAME / DARWIN_DATASET_NAME,
)
@pytest.mark.usefixtures("file_read_write_test")
def test_split_video_annotations_on_videos(*mocks):
    create_annotation_file(
        name="test_video.json",
        content=video_annotation_file_content(),
        team_name=DARWIN_TEAM_NAME,
        dataset_name=DARWIN_DATASET_NAME,
    )

    client = _load_client(offline=True)
    remote_dataset = RemoteDataset(
        client=client, team=DARWIN_TEAM_NAME, name=DARWIN_DATASET_NAME, slug="test-dataset", dataset_id=1
    )

    remote_dataset.split_video_annotations()

    for mock in mocks:
        mock.assert_called()

    video_path = (
        DARWIN_TEST_PATH / DARWIN_TEAM_NAME / DARWIN_DATASET_NAME / "releases" / "latest" / "annotations" / "test_video"
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
