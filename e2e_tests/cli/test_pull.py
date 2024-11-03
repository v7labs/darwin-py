from pathlib import Path

from e2e_tests.helpers import assert_cli, run_cli_command, export_release
from e2e_tests.objects import E2EDataset, ConfigValues


def test_pull_with_remote_folder_structure(
    local_dataset: E2EDataset, config_values: ConfigValues
):
    """
    Test pulling a dataset release with default arguments.

    The remote directory structure should be recreated locally.
    """
    pull_dir = Path(
        f"{Path.home()}/.darwin/datasets/{config_values.team_slug}/{local_dataset.slug}/images"
    )
    expected_filepaths = [
        f"{pull_dir}/image_1",
        f"{pull_dir}/image_2",
        f"{pull_dir}/dir1/image_3",
        f"{pull_dir}/dir1/image_4",
        f"{pull_dir}/dir2/image_5",
        f"{pull_dir}/dir2/image_6",
        f"{pull_dir}/dir1/dir3/image_7",
        f"{pull_dir}/dir1/dir3/image_8",
    ]
    item_type = "single_slotted"
    annotation_format = "darwin"
    local_dataset.register_read_only_items(config_values, item_type)
    release = export_release(annotation_format, local_dataset, config_values)
    result = run_cli_command(f"darwin dataset pull {local_dataset.name}:{release.name}")
    assert_cli(result, 0)
    all_filepaths = list(pull_dir.rglob("*"))
    for expected_file in expected_filepaths:
        assert Path(expected_file) in all_filepaths
