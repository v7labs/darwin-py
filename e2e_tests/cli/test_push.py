from pathlib import Path


from e2e_tests.helpers import (
    assert_cli,
    run_cli_command,
    wait_until_items_processed,
    list_items,
)
from e2e_tests.objects import E2EDataset, ConfigValues

import tempfile
import zipfile


def test_push_mixed_filetypes(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test pushing a directory of files containing various fileytypes:
    - .jpg
    - .png
    - .mp4
    - .dcm
    - .pdf
    """
    push_dir = Path(__file__).parents[1] / "data" / "push" / "mixed_filetypes.zip"
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/mixed_filetypes"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, local_dataset.id)
            items = list_items(
                config_values.api_key,
                local_dataset.id,
                config_values.team_slug,
                config_values.server,
            )
            assert len(items) == 5


def test_push_nested_directory_of_images(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test pushing a nested directory structure of some images with the `preserve_folders` flag.
    """
    expected_paths = {
        "image_1.jpg": "/dir1",
        "image_2.jpg": "/dir1",
        "image_3.jpg": "/dir2",
        "image_4.jpg": "/dir2",
        "image_5.jpg": "/dir1/dir3",
        "image_6.jpg": "/dir1/dir3",
    }
    push_dir = (
        Path(__file__).parents[1] / "data" / "push" / "nested_directory_of_images.zip"
    )
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/nested_directory_of_images --preserve-folders"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, local_dataset.id)
            items = list_items(
                config_values.api_key,
                local_dataset.id,
                config_values.team_slug,
                config_values.server,
            )
            assert len(items) == 6
            for item in items:
                assert expected_paths[item["name"]] == item["path"]


def test_push_videos_with_non_native_fps(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test that if FPS is set, that the value is respected in the resulting dataset items
    """
    push_dir = Path(__file__).parents[1] / "data" / "push" / "25_frame_video.zip"
    fps = 5
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/25_frame_video --fps {fps}"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, local_dataset.id)
            items = list_items(
                config_values.api_key,
                local_dataset.id,
                config_values.team_slug,
                config_values.server,
            )
            video_metadata = items[0]["slots"][0]["metadata"]
            assert len(items) == 1
            assert 1 == 1
            assert items[0]["slots"][0]["fps"] == fps
            assert video_metadata["native_fps"] == 10
            assert video_metadata["frames_manifests"][0]["total_frames"] == 25
            assert video_metadata["frames_manifests"][0]["visible_frames"] == 13
