import pytest
from darwin.dataset.identifier import DatasetIdentifier


class TestDatasetIdentifier:
    class TestParse:
        def test_no_slash(self):
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("no-slash")

        def test_team_only(self):
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("team/")

        def test_dataset_only(self):
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("/dataset")

        def test_missing_version(self):
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("team/dataset:")

        def test_no_alphanumeric_characters(self):
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("no_alphanumeric")

        def test_standard_format(self):
            dataset_identifier = DatasetIdentifier.parse("team/dataset")
            assert dataset_identifier.team_slug == "team"
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version is None

        def test_with_version(self):
            dataset_identifier = DatasetIdentifier.parse("team/dataset:1.0")
            assert dataset_identifier.team_slug == "team"
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version == "1.0"

        def test_with_dashes(self):
            dataset_identifier = DatasetIdentifier.parse("my-team/my-dataset")
            assert dataset_identifier.team_slug == "my-team"
            assert dataset_identifier.dataset_slug == "my-dataset"
            assert dataset_identifier.version is None

        def test_with_numbers(self):
            dataset_identifier = DatasetIdentifier.parse("team1/dataset1")
            assert dataset_identifier.team_slug == "team1"
            assert dataset_identifier.dataset_slug == "dataset1"
            assert dataset_identifier.version is None
