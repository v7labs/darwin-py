from pathlib import Path
from re import split
from shutil import copyfile
from unittest.mock import MagicMock, patch

import pytest
from darwin.dataset.local_dataset import build_stems
from tests.fixtures import *


@pytest.mark.usefixtures("file_read_write_test")
def describe__build_stems():
    def look_into_annotations_directory_if_no_partition_specified(
        team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        (annotations_path / "1.json").mkdir()
        (annotations_path / "2" / "2.json").mkdir(parents=True)
        (annotations_path / "test" / "3" / "3.json").mkdir(parents=True)

        stems = list(build_stems(team_dataset_release_path, annotations_path, "tag", split_path.name))

        assert "1" in stems
        assert "2/2" in stems or "2\\2" in stems
        assert "test/3/3" in stems or "test\\3\\3" in stems

    def raise_value_error_if_split_type_is_unknown(
        team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        with pytest.raises(ValueError) as e:
            build_stems(team_dataset_release_path, annotations_path, "tag", split_path.name, "train", "unknown")

        assert str(e.value) == 'Unknown split type "unknown"'

    def stems_ending_with_spaces(team_dataset_release_path: Path, annotations_path: Path, split_path: Path):
        resource_file = Path("tests") / "darwin" / "dataset" / "resources" / "random_train"
        copyfile(resource_file, split_path / "random_train.txt")

        stems = list(build_stems(team_dataset_release_path, annotations_path, "tag", split_path.name, "train"))

        assert "one" in stems
        assert "two " in stems
        assert "three  " in stems

    def raise_file_not_found_if_split_file_does_not_exists(
        team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        with pytest.raises(FileNotFoundError) as e:
            build_stems(team_dataset_release_path, annotations_path, "tag", split_path.name, "train")

        assert (
            str(e.value)
            == "could not find a dataset partition. Split the dataset using `split_dataset()` from `darwin.dataset.split_manager`"
        )
