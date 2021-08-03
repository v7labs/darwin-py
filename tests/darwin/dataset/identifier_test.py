import pytest
from darwin.dataset.identifier import DatasetIdentifier


def describe_dataset_identifier():
    def describe_parse():
        def raises_with_team_only():
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("team/")

        def raises_with_dataset_only():
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("/dataset")

        def raises_with_missing_version():
            with pytest.raises(ValueError):
                DatasetIdentifier.parse("team/dataset:")

        def allows_underscores():
            dataset_identifier = DatasetIdentifier.parse("with_underscore")
            assert dataset_identifier.dataset_slug == "with_underscore"

        def standard_format():
            dataset_identifier = DatasetIdentifier.parse("team/dataset")
            assert dataset_identifier.team_slug == "team"
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version is None

        def optional_team():
            dataset_identifier = DatasetIdentifier.parse("dataset")
            assert dataset_identifier.team_slug is None
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version is None

        def with_version():
            dataset_identifier = DatasetIdentifier.parse("team/dataset:1.0")
            assert dataset_identifier.team_slug == "team"
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version == "1.0"

        def with_version_with_underscores():
            dataset_identifier = DatasetIdentifier.parse("team/dataset:1_0-3")
            assert dataset_identifier.team_slug == "team"
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version == "1_0-3"

        def optional_team_with_version():
            dataset_identifier = DatasetIdentifier.parse("dataset:1.0")
            assert dataset_identifier.team_slug is None
            assert dataset_identifier.dataset_slug == "dataset"
            assert dataset_identifier.version == "1.0"

        def with_dashes():
            dataset_identifier = DatasetIdentifier.parse("my-team/my-dataset")
            assert dataset_identifier.team_slug == "my-team"
            assert dataset_identifier.dataset_slug == "my-dataset"
            assert dataset_identifier.version is None

        def with_numbers():
            dataset_identifier = DatasetIdentifier.parse("team1/dataset1")
            assert dataset_identifier.team_slug == "team1"
            assert dataset_identifier.dataset_slug == "dataset1"
            assert dataset_identifier.version is None
