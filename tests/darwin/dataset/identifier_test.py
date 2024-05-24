import pytest

from darwin.dataset.identifier import DatasetIdentifier


class TestDatasetIdentifier:
    def test_raises_with_team_only(self):
        with pytest.raises(ValueError):
            DatasetIdentifier.parse("team/")

    def test_raises_with_dataset_only(self):
        with pytest.raises(ValueError):
            DatasetIdentifier.parse("/dataset")

    def test_raises_with_missing_version(self):
        with pytest.raises(ValueError):
            DatasetIdentifier.parse("team/dataset:")

    def test_allows_underscores(self):
        dataset_identifier = DatasetIdentifier.parse("with_underscore")
        assert dataset_identifier.dataset_slug == "with_underscore"

    def test_standard_format(self):
        dataset_identifier = DatasetIdentifier.parse("team/dataset")
        assert dataset_identifier.team_slug == "team"
        assert dataset_identifier.dataset_slug == "dataset"
        assert dataset_identifier.version is None

    def test_optional_team(self):
        dataset_identifier = DatasetIdentifier.parse("dataset")
        assert dataset_identifier.team_slug is None
        assert dataset_identifier.dataset_slug == "dataset"
        assert dataset_identifier.version is None

    def test_with_version(self):
        dataset_identifier = DatasetIdentifier.parse("team/dataset:1.0")
        assert dataset_identifier.team_slug == "team"
        assert dataset_identifier.dataset_slug == "dataset"
        assert dataset_identifier.version == "1.0"

    def test_with_version_with_underscores(self):
        dataset_identifier = DatasetIdentifier.parse("team/dataset:1_0-3")
        assert dataset_identifier.team_slug == "team"
        assert dataset_identifier.dataset_slug == "dataset"
        assert dataset_identifier.version == "1_0-3"

    def test_optional_team_with_version(self):
        dataset_identifier = DatasetIdentifier.parse("dataset:1.0")
        assert dataset_identifier.team_slug is None
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
