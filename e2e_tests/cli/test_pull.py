from pathlib import Path

from e2e_tests.helpers import assert_cli, run_cli_command, export_release
from e2e_tests.objects import E2EDataset, ConfigValues, TeamConfigValues


def test_pull_with_remote_folder_structure(
    local_dataset: E2EDataset,
    config_values: ConfigValues,
    isolated_team: TeamConfigValues,
):
    """
    Test pulling a dataset release with default arguments.

    The remote directory structure should be recreated locally.
    """
    pull_dir = Path(
        f"{Path.home()}/.darwin/datasets/{isolated_team.team_slug}/{local_dataset.slug}/images"
    )
    expected_filepaths = [
        f"{pull_dir}/image_1.jpg",
        f"{pull_dir}/image_2.jpg",
        f"{pull_dir}/dir1/image_3.jpg",
        f"{pull_dir}/dir1/image_4.jpg",
        f"{pull_dir}/dir2/image_5.jpg",
        f"{pull_dir}/dir2/image_6.jpg",
        f"{pull_dir}/dir1/dir3/image_7.jpg",
        f"{pull_dir}/dir1/dir3/image_8.jpg",
    ]
    item_type = "single_slotted"
    annotation_format = "darwin"
    local_dataset.register_read_only_items(config_values, isolated_team, item_type)
    release = export_release(
        annotation_format, local_dataset, config_values, isolated_team
    )
    result = run_cli_command(f"darwin dataset pull {local_dataset.name}:{release.name}")
    assert_cli(result, 0)
    all_filepaths = list(pull_dir.rglob("*"))
    for expected_file in expected_filepaths:
        assert Path(expected_file) in all_filepaths
