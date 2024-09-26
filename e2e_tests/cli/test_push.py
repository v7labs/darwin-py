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


def test_push_multi_slotted_item(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test pushing a multi-slotted item with the CLI. Check the resulting item is
    structured as expected
    """
    expected_name = "flat_directory_of_6_images"
    expected_slot_types = ["image", "image", "image", "image", "image", "image"]
    expected_layout = {
        "slots_grid": [[["0"], ["3"]], [["1"], ["4"]], [["2"], ["5"]]],
        "version": 3,
    }
    expected_file_names = [
        "image_1.jpg",
        "image_2.jpg",
        "image_3.jpg",
        "image_4.jpg",
        "image_5.jpg",
        "image_6.jpg",
    ]
    push_dir = (
        Path(__file__).parents[1] / "data" / "push" / "flat_directory_of_6_images.zip"
    )
    merge_mode = "slots"
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/flat_directory_of_6_images --item-merge-mode {merge_mode}"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, local_dataset.id)
            items = list_items(
                config_values.api_key,
                local_dataset.id,
                config_values.team_slug,
                config_values.server,
            )
            assert len(items) == 1
            multi_slotted_item = items[0]
            assert multi_slotted_item["name"] == expected_name
            assert multi_slotted_item["slot_types"] == expected_slot_types
            assert multi_slotted_item["layout"] == expected_layout
            for num, slot in enumerate(multi_slotted_item["slots"]):
                assert slot["slot_name"] == str(num)
                assert slot["file_name"] == expected_file_names[num]


def test_push_multi_channel_item(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test pushing a multi-channel item with the CLI. Check the resulting item is
    structured as expected
    """
    expected_name = "flat_directory_of_6_images"
    expected_slot_types = ["image", "image", "image", "image", "image", "image"]
    expected_layout = {
        "slots_grid": [
            [
                [
                    "image_1.jpg",
                    "image_2.jpg",
                    "image_3.jpg",
                    "image_4.jpg",
                    "image_5.jpg",
                    "image_6.jpg",
                ]
            ]
        ],
        "version": 3,
    }
    expected_file_names = [
        "image_1.jpg",
        "image_2.jpg",
        "image_3.jpg",
        "image_4.jpg",
        "image_5.jpg",
        "image_6.jpg",
    ]
    push_dir = (
        Path(__file__).parents[1] / "data" / "push" / "flat_directory_of_6_images.zip"
    )
    merge_mode = "channels"
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/flat_directory_of_6_images --item-merge-mode {merge_mode}"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, local_dataset.id)
            items = list_items(
                config_values.api_key,
                local_dataset.id,
                config_values.team_slug,
                config_values.server,
            )
            assert len(items) == 1
            multi_channel_item = items[0]
            assert multi_channel_item["name"] == expected_name
            assert multi_channel_item["slot_types"] == expected_slot_types
            assert multi_channel_item["layout"] == expected_layout
            for num, slot in enumerate(multi_channel_item["slots"]):
                assert slot["slot_name"] == expected_file_names[num]
                assert slot["file_name"] == expected_file_names[num]


def test_push_dicom_series(
    local_dataset: E2EDataset, config_values: ConfigValues
) -> None:
    """
    Test pushing a multi-file DICOM item with the CLI. Check the resulting item is
    structured as expected
    """
    expected_name = "flat_directory_of_2_dicom_files"
    expected_slot_types = [
        "dicom",
        "dicom",
    ]
    expected_layout = {
        "slots_grid": [
            [
                [
                    "flat_directory_of_2_dicom_files",
                ]
            ]
        ],
        "version": 3,
    }
    expected_file_names = [
        "flat_directory_of_2_dicom_files",
    ]
    push_dir = (
        Path(__file__).parents[1]
        / "data"
        / "push"
        / "flat_directory_of_2_dicom_files.zip"
    )
    merge_mode = "series"
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/flat_directory_of_2_dicom_files --item-merge-mode {merge_mode}"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, local_dataset.id)
            items = list_items(
                config_values.api_key,
                local_dataset.id,
                config_values.team_slug,
                config_values.server,
            )
            assert len(items) == 1
            dicom_series_item = items[0]
            assert dicom_series_item["name"] == expected_name
            assert dicom_series_item["slot_types"] == expected_slot_types
            assert dicom_series_item["layout"] == expected_layout
            for num, slot in enumerate(dicom_series_item["slots"]):
                assert slot["slot_name"] == expected_file_names[num]
