"""
E2E tests for readonly video registration.

Prerequisites:
- External storage configured in Darwin (darwin-e2e-data)
- AWS credentials available (via OIDC in CI or environment variables locally)
- Source video pre-uploaded to darwin-py/source-videos/ in S3
"""

import shutil
from pathlib import Path
from typing import Generator, List

import pytest

from darwin.client import Client
from darwin.dataset.identifier import DatasetIdentifier
from darwin.datatypes import ObjectStore
from e2e_tests.conftest import ARTIFACTS_PREFIX, SOURCE_VIDEOS_PREFIX
from e2e_tests.helpers import cleanup_s3_prefix, list_items, new_dataset  # noqa: F401
from e2e_tests.objects import ConfigValues, E2EDataset

# Test video key in S3
TEST_VIDEO_KEY = f"{SOURCE_VIDEOS_PREFIX}/short_video.mp4"


@pytest.fixture
def downloaded_test_video(
    e2e_video_storage: ObjectStore, s3_client, tmp_path: Path
) -> Generator[Path, None, None]:
    """
    Download test video from S3 to local temp directory.

    The video is downloaded at test start and cleaned up after the test.
    """
    local_path = tmp_path / "test_video.mp4"

    try:
        print(
            f"Downloading test video from s3://{e2e_video_storage.bucket}/{TEST_VIDEO_KEY}"
        )
        s3_client.download_file(
            e2e_video_storage.bucket, TEST_VIDEO_KEY, str(local_path)
        )
    except Exception as e:
        pytest.fail(f"Failed to download test video from S3: {e}")

    yield local_path


@pytest.fixture
def uploaded_artifacts_tracker(
    artifacts_storage: ObjectStore,
) -> Generator[List[str], None, None]:
    """
    Track uploaded artifact prefixes for cleanup after test.

    Yields a list that tests can append prefixes to.
    After the test, all tracked prefixes are deleted from S3.
    """
    tracked_prefixes: List[str] = []
    yield tracked_prefixes

    # Cleanup after test
    if tracked_prefixes:
        print(f"\nCleaning up {len(tracked_prefixes)} artifact prefix(es)...")
        total_deleted = 0
        for prefix in tracked_prefixes:
            deleted = cleanup_s3_prefix(
                artifacts_storage.bucket, prefix, artifacts_storage.region
            )
            total_deleted += deleted
        print(f"Deleted {total_deleted} artifact(s) from S3")


class TestReadonlyVideoRegistration:
    """E2E tests for readonly video registration with automatic cleanup."""

    def test_register_single_slotted_video(
        self,
        new_dataset: E2EDataset,  # noqa: F811
        config_values: ConfigValues,
        artifacts_storage: ObjectStore,
        downloaded_test_video: Path,
        uploaded_artifacts_tracker: List[str],
    ) -> None:
        """Test registering a single video as a single-slotted item."""
        client = Client.from_api_key(api_key=config_values.api_key)
        dataset_identifier = DatasetIdentifier(
            dataset_slug=new_dataset.slug,
            team_slug=config_values.team_slug,
        )
        dataset = client.get_remote_dataset(dataset_identifier=dataset_identifier)

        # Track the artifacts prefix for cleanup
        # The actual prefix will be: ARTIFACTS_PREFIX/item_uuid/files/slot_uuid
        # We track the base prefix to clean up all artifacts
        uploaded_artifacts_tracker.append(ARTIFACTS_PREFIX)

        # Register video
        results = dataset.register_single_slotted_readonly_videos(
            object_store=artifacts_storage,
            video_files=[downloaded_test_video],
            path="/e2e-test",
            fps=1.0,
            segment_length=2,
        )

        # Assertions
        assert (
            "registered" in results
        ), f"Expected 'registered' key in results: {results}"
        assert len(results["registered"]) == 1, f"Expected 1 registered item: {results}"
        assert (
            downloaded_test_video.name in results["registered"][0]
        ), f"Expected video name in result: {results}"

        # Verify item exists in Darwin
        items = list_items(
            config_values.api_key,
            new_dataset.id,
            config_values.team_slug,
            config_values.server,
        )
        assert len(items) == 1, f"Expected 1 item in dataset, got {len(items)}"
        assert items[0]["name"] == downloaded_test_video.name
        assert items[0]["slot_types"] == ["video"]

    def test_register_multi_slotted_video(
        self,
        new_dataset: E2EDataset,  # noqa: F811
        config_values: ConfigValues,
        artifacts_storage: ObjectStore,
        downloaded_test_video: Path,
        uploaded_artifacts_tracker: List[str],
        tmp_path: Path,
    ) -> None:
        """Test registering multiple videos as a multi-slotted item."""
        # Create a second video by copying the first one
        second_video = tmp_path / "test_video_2.mp4"
        shutil.copy(downloaded_test_video, second_video)

        client = Client.from_api_key(api_key=config_values.api_key)
        dataset_identifier = DatasetIdentifier(
            dataset_slug=new_dataset.slug,
            team_slug=config_values.team_slug,
        )
        dataset = client.get_remote_dataset(dataset_identifier=dataset_identifier)

        # Track artifacts for cleanup
        uploaded_artifacts_tracker.append(ARTIFACTS_PREFIX)

        item_name = "multi_view_test"
        results = dataset.register_multi_slotted_readonly_videos(
            object_store=artifacts_storage,
            video_files={item_name: [downloaded_test_video, second_video]},
            path="/e2e-test",
            fps=1.0,
            segment_length=2,
        )

        # Assertions
        assert (
            "registered" in results
        ), f"Expected 'registered' key in results: {results}"
        assert len(results["registered"]) == 1, f"Expected 1 registered item: {results}"

        # Verify item exists in Darwin with correct structure
        items = list_items(
            config_values.api_key,
            new_dataset.id,
            config_values.team_slug,
            config_values.server,
        )
        assert len(items) == 1, f"Expected 1 item in dataset, got {len(items)}"

        multi_slot_item = items[0]
        assert multi_slot_item["name"] == item_name
        assert (
            len(multi_slot_item["slots"]) == 2
        ), "Expected 2 slots in multi-slotted item"
        assert multi_slot_item["slot_types"] == ["video", "video"]


if __name__ == "__main__":
    pytest.main(["-vv", "-s", __file__])
