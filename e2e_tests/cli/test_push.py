import tempfile
import zipfile
from pathlib import Path

from e2e_tests.helpers import (
    assert_cli,
    list_items,
    run_cli_command,
    wait_until_items_processed,
)
from e2e_tests.logger_config import logger
from e2e_tests.objects import ConfigValues, E2EDataset, E2EItem, TeamConfigValues


def extract_and_push(
    push_dir,
    local_dataset,
    config_values,
    isolated_team,
    expected_push_dir,
    extra_args="",
):
    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        with zipfile.ZipFile(push_dir) as z:
            z.extractall(tmp_dir)
            result = run_cli_command(
                f"darwin dataset push {local_dataset.name} {tmp_dir}/{expected_push_dir} {extra_args}"
            )
            assert_cli(result, 0)
            wait_until_items_processed(config_values, isolated_team, local_dataset.id)
            items = list_items(
                isolated_team.api_key,
                local_dataset.id,
                isolated_team.team_slug,
                config_values.server,
            )
            for item in items:
                local_dataset.add_item(
                    E2EItem(
                        name=item["name"],
                        id=item["id"],
                        path=item["path"],
                        file_name=item["name"],
                        slot_name=item["slots"][0]["file_name"],
                        annotations=[],
                    )
                )
            return items


def test_push_mixed_filetypes(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Test pushing a directory of files containing various fileytypes:
    - .jpg
    - .png
    - .mp4
    - .dcm
    - .pdf
    """
    expected_push_dir = "mixed_filetypes"
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{expected_push_dir}.zip"
    logger.info(f"Starting push test for team {isolated_team.team_slug}")
    items = extract_and_push(
        push_dir, local_dataset, config_values, isolated_team, expected_push_dir
    )
    assert len(items) == 5
    logger.info("Push operation completed successfully")


def test_push_nested_directory_of_images(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Test pushing a nested directory structure of some images with the `preserve_folders` flag.
    """
    expected_push_dir = "nested_directory_of_images"
    expected_paths = {
        "image_1.jpg": "/dir1",
        "image_2.jpg": "/dir1",
        "image_3.jpg": "/dir2",
        "image_4.jpg": "/dir2",
        "image_5.jpg": "/dir1/dir3",
        "image_6.jpg": "/dir1/dir3",
    }
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{expected_push_dir}.zip"
    logger.info(f"Starting push test for team {isolated_team.team_slug}")
    items = extract_and_push(
        push_dir,
        local_dataset,
        config_values,
        isolated_team,
        expected_push_dir,
        "--preserve-folders",
    )
    assert len(items) == 6
    for item in items:
        assert expected_paths[item["name"]] == item["path"]
    logger.info("Push operation completed successfully")


def test_push_videos_with_non_native_fps(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Test that if FPS is set, that the value is respected in the resulting dataset items
    """
    expected_push_dir = "25_frame_video"
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{expected_push_dir}.zip"
    fps = 5
    logger.info(f"Starting push test for team {isolated_team.team_slug}")
    items = extract_and_push(
        push_dir,
        local_dataset,
        config_values,
        isolated_team,
        expected_push_dir,
        f"--fps {fps}",
    )
    video_metadata = items[0]["slots"][0]["metadata"]
    assert len(items) == 1
    assert items[0]["slots"][0]["fps"] == fps
    assert video_metadata["native_fps"] == 10
    assert video_metadata["frames_manifests"][0]["total_frames"] == 25
    assert video_metadata["frames_manifests"][0]["visible_frames"] == 13
    logger.info("Push operation completed successfully")


def test_push_multi_slotted_item(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Test pushing a multi-slotted item with the CLI. Check the resulting item is
    structured as expected
    """
    expected_push_dir = "flat_directory_of_6_images"
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
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{expected_push_dir}.zip"
    logger.info(f"Starting push test for team {isolated_team.team_slug}")
    items = extract_and_push(
        push_dir,
        local_dataset,
        config_values,
        isolated_team,
        expected_push_dir,
        "--item-merge-mode slots",
    )
    assert len(items) == 1
    multi_slotted_item = items[0]
    assert multi_slotted_item["name"] == expected_name
    assert multi_slotted_item["slot_types"] == expected_slot_types
    assert multi_slotted_item["layout"] == expected_layout
    for num, slot in enumerate(multi_slotted_item["slots"]):
        assert slot["slot_name"] == str(num)
        assert slot["file_name"] == expected_file_names[num]
    logger.info("Push operation completed successfully")


def test_push_multi_channel_item(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Test pushing a multi-channel item with the CLI. Check the resulting item is
    structured as expected
    """
    expected_push_dir = "flat_directory_of_6_images"
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
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{expected_push_dir}.zip"
    logger.info(f"Starting push test for team {isolated_team.team_slug}")
    items = extract_and_push(
        push_dir,
        local_dataset,
        config_values,
        isolated_team,
        expected_push_dir,
        "--item-merge-mode channels",
    )
    assert len(items) == 1
    multi_channel_item = items[0]
    assert multi_channel_item["name"] == expected_name
    assert multi_channel_item["slot_types"] == expected_slot_types
    assert multi_channel_item["layout"] == expected_layout
    for num, slot in enumerate(multi_channel_item["slots"]):
        assert slot["slot_name"] == expected_file_names[num]
        assert slot["file_name"] == expected_file_names[num]
    logger.info("Push operation completed successfully")


def test_push_dicom_series(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
) -> None:
    """
    Test pushing a multi-file DICOM item with the CLI. Check the resulting item is
    structured as expected
    """
    expected_push_dir = "flat_directory_of_2_dicom_files"
    expected_name = "flat_directory_of_2_dicom_files"
    expected_slot_types = ["dicom"]
    expected_layout = {"slots": ["0"], "type": "simple", "version": 1}
    push_dir = Path(__file__).parents[1] / "data" / "push" / f"{expected_push_dir}.zip"
    logger.info(f"Starting push test for team {isolated_team.team_slug}")
    items = extract_and_push(
        push_dir,
        local_dataset,
        config_values,
        isolated_team,
        expected_push_dir,
        "--item-merge-mode series",
    )
    assert len(items) == 1
    dicom_series_item = items[0]
    assert dicom_series_item["name"] == expected_name
    assert dicom_series_item["slot_types"] == expected_slot_types
    assert dicom_series_item["layout"] == expected_layout
    for num, slot in enumerate(dicom_series_item["slots"]):
        assert slot["slot_name"] == "0"
    logger.info("Push operation completed successfully")
