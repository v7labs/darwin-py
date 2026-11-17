"""
E2E tests for readonly image registration.

Prerequisites:
- External storage configured in Darwin (darwin-e2e-data)
- AWS credentials available (via OIDC in CI or environment variables locally)
- Source video pre-uploaded to darwin-py/source-videos/ in S3 (mixed test only)

The source images are generated locally with Pillow, so no pre-uploaded
image is required.
"""

import io
from pathlib import Path
from typing import Dict, List

import pytest
import requests
from PIL import Image

from darwin.client import Client
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.datatypes import ObjectStore
from darwin.extractor.image import THUMBNAIL_MAX_SIZE
from e2e_tests.conftest import ARTIFACTS_PREFIX
from e2e_tests.helpers import new_dataset  # noqa: F401
from e2e_tests.objects import ConfigValues, E2EDataset
from e2e_tests.sdk.test_readonly_video import (  # noqa: F401
    downloaded_test_video,
    uploaded_artifacts_tracker,
)


def _create_test_image(path: Path, size=(640, 480)) -> Path:
    image = Image.linear_gradient("L").resize(size).convert("RGB")
    image.save(path, quality=90)
    return path


def _get_dataset(config_values: ConfigValues, dataset: E2EDataset) -> RemoteDatasetV2:
    client = Client.from_api_key(api_key=config_values.api_key)
    dataset_identifier = DatasetIdentifier(
        dataset_slug=dataset.slug,
        team_slug=config_values.team_slug,
    )
    remote_dataset = client.get_remote_dataset(dataset_identifier=dataset_identifier)
    assert isinstance(remote_dataset, RemoteDatasetV2)
    return remote_dataset


def _list_items_with_thumbnails(
    config_values: ConfigValues, dataset_id: int
) -> List[Dict]:
    response = requests.get(
        f"{config_values.server}/api/v2/teams/{config_values.team_slug}/items",
        params={"dataset_ids": dataset_id, "include_thumbnails": "true"},
        headers={
            "accept": "application/json",
            "Authorization": f"ApiKey {config_values.api_key}",
        },
    )
    response.raise_for_status()
    return response.json()["items"]


def _assert_image_slot(slot: Dict, source: Path, size) -> None:
    assert slot["type"] == "image"
    assert slot["file_name"] == source.name
    assert slot["metadata"]["width"] == size[0]
    assert slot["metadata"]["height"] == size[1]
    assert slot["size_bytes"] == source.stat().st_size

    thumbnail_url = slot.get("thumbnail_url")
    assert thumbnail_url, f"Expected a thumbnail URL in slot: {slot}"
    response = requests.get(thumbnail_url)
    assert response.ok, f"Failed to download thumbnail: {response.status_code}"
    with Image.open(io.BytesIO(response.content)) as thumbnail:
        assert thumbnail.format == "JPEG"
        assert thumbnail.width <= THUMBNAIL_MAX_SIZE[0]
        assert thumbnail.height <= THUMBNAIL_MAX_SIZE[1]


class TestReadonlyImageRegistration:
    """E2E tests for readonly image registration with automatic cleanup."""

    def test_register_single_slotted_image(
        self,
        new_dataset: E2EDataset,  # noqa: F811
        config_values: ConfigValues,
        artifacts_storage: ObjectStore,
        uploaded_artifacts_tracker: List[str],  # noqa: F811
        tmp_path: Path,
    ) -> None:
        """Test registering a single image as a single-slotted item."""
        image = _create_test_image(tmp_path / "test_image.jpg", size=(640, 480))
        dataset = _get_dataset(config_values, new_dataset)

        # Track the artifacts prefix for cleanup
        uploaded_artifacts_tracker.append(ARTIFACTS_PREFIX)

        results = dataset.register_single_slotted_readonly_images(
            object_store=artifacts_storage,
            image_files=[image],
            path="/e2e-test",
        )

        assert len(results["registered"]) == 1, f"Expected 1 registered item: {results}"
        assert image.name in results["registered"][0]

        items = _list_items_with_thumbnails(config_values, new_dataset.id)
        assert len(items) == 1, f"Expected 1 item in dataset, got {len(items)}"
        assert items[0]["name"] == image.name
        assert items[0]["path"] == "/e2e-test"
        assert items[0]["slot_types"] == ["image"]
        _assert_image_slot(items[0]["slots"][0], image, (640, 480))

    def test_register_multi_slotted_images(
        self,
        new_dataset: E2EDataset,  # noqa: F811
        config_values: ConfigValues,
        artifacts_storage: ObjectStore,
        uploaded_artifacts_tracker: List[str],  # noqa: F811
        tmp_path: Path,
    ) -> None:
        """Test registering two images as one multi-slotted item."""
        left = _create_test_image(tmp_path / "left.png", size=(320, 240))
        right = _create_test_image(tmp_path / "right.jpg", size=(200, 400))
        dataset = _get_dataset(config_values, new_dataset)

        uploaded_artifacts_tracker.append(ARTIFACTS_PREFIX)

        item_name = "multi_image_test"
        results = dataset.register_locally_processed(
            object_store=artifacts_storage,
            files={item_name: [left, right]},
            path="/e2e-test",
            multi_slotted=True,
        )

        assert len(results["registered"]) == 1, f"Expected 1 registered item: {results}"

        items = _list_items_with_thumbnails(config_values, new_dataset.id)
        assert len(items) == 1, f"Expected 1 item in dataset, got {len(items)}"
        item = items[0]
        assert item["name"] == item_name
        assert item["slot_types"] == ["image", "image"]
        slots = {slot["slot_name"]: slot for slot in item["slots"]}
        assert set(slots) == {"left.png", "right.jpg"}
        _assert_image_slot(slots["left.png"], left, (320, 240))
        _assert_image_slot(slots["right.jpg"], right, (200, 400))

    def test_register_mixed_video_and_image(
        self,
        new_dataset: E2EDataset,  # noqa: F811
        config_values: ConfigValues,
        artifacts_storage: ObjectStore,
        downloaded_test_video: Path,  # noqa: F811
        uploaded_artifacts_tracker: List[str],  # noqa: F811
        tmp_path: Path,
    ) -> None:
        """Test registering a video and an image in one multi-slotted item."""
        image = _create_test_image(tmp_path / "frame.jpg", size=(640, 360))
        dataset = _get_dataset(config_values, new_dataset)

        uploaded_artifacts_tracker.append(ARTIFACTS_PREFIX)

        item_name = "mixed_video_image_test"
        results = dataset.register_locally_processed(
            object_store=artifacts_storage,
            files={item_name: [downloaded_test_video, image]},
            path="/e2e-test",
            fps=1.0,
            segment_length=2,
            multi_slotted=True,
        )

        assert len(results["registered"]) == 1, f"Expected 1 registered item: {results}"

        items = _list_items_with_thumbnails(config_values, new_dataset.id)
        assert len(items) == 1, f"Expected 1 item in dataset, got {len(items)}"
        item = items[0]
        assert item["name"] == item_name
        assert sorted(item["slot_types"]) == ["image", "video"]
        slots = {slot["slot_name"]: slot for slot in item["slots"]}
        assert slots[downloaded_test_video.name]["type"] == "video"
        _assert_image_slot(slots[image.name], image, (640, 360))


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
