from pathlib import Path
from shutil import copyfile

import pytest

from darwin.dataset.local_dataset import get_annotation_filepaths
from tests.fixtures import *


@pytest.mark.usefixtures("file_read_write_test")
class TestGetAnnotationFilepaths:
    def test_raise_value_error_if_split_type_is_unknown(
        self, team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        with pytest.raises(ValueError) as e:
            get_annotation_filepaths(
                team_dataset_release_path,
                annotations_path,
                "tag",
                split_path.name,
                "train",
                "unknown",
            )

        assert str(e.value) == 'Unknown split type "unknown"'

    def test_annotation_filepaths_ending_with_spaces(
        self, team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        resource_file = (
            Path("tests") / "darwin" / "dataset" / "resources" / "random_train"
        )
        copyfile(resource_file, split_path / "random_train.txt")

        annotation_filepaths = list(
            get_annotation_filepaths(
                team_dataset_release_path,
                annotations_path,
                "tag",
                split_path.name,
                "train",
            )
        )

        assert "path/to/annotation/file/one.json " in annotation_filepaths
        assert "path/to/annotation/file/two.json   " in annotation_filepaths
        assert "three.json  " in annotation_filepaths

    def test_raise_file_not_found_if_split_file_does_not_exists(
        self, team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        with pytest.raises(FileNotFoundError) as e:
            get_annotation_filepaths(
                team_dataset_release_path,
                annotations_path,
                "tag",
                split_path.name,
                "train",
            )

        assert (
            str(e.value)
            == "could not find a dataset partition. Split the dataset using `split_dataset()` from `darwin.dataset.split_manager`"
        )

    def test_get_annotation_filepaths_no_partition(
        self, team_dataset_release_path: Path, annotations_path: Path, split_path: Path
    ):
        (annotations_path / "1.json").mkdir()
        (annotations_path / "2" / "2.json").mkdir(parents=True)
        (annotations_path / "test" / "3" / "3.json").mkdir(parents=True)

        annotation_filepaths = list(
            get_annotation_filepaths(
                team_dataset_release_path,
                annotations_path,
                "tag",
                split_path.name,
                None,
            )
        )

        assert str(annotations_path / "1.json") in annotation_filepaths
        assert str(annotations_path / "2/2.json") in annotation_filepaths
        assert str(annotations_path / "test/3/3.json") in annotation_filepaths
