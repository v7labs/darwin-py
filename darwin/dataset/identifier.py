import re
from typing import Optional, Tuple, Union


class DatasetIdentifier:
    """
    Formal representation of a dataset identifier for the SDK.

    A dataset identifier is a string that uniquely identifies a dataset on Darwin.
    A dataset identifier is made of the following substrings:
    ``<team-slug>/<dataset-slug>:<version>``.

    If ``version`` is missing, it defaults to ``latest``.

    Parameters
    ----------
    dataset_slug : str
        The slugified name of the dataset.
    team_slug : Optional[str], default: None
        The slugified name of the team.
    version : Optional[str], default: None
        The version of the identifier.

    Attributes
    ----------
    dataset_slug : str
        The slugified name of the dataset.
    team_slug : Optional[str], default: None
        The slugified name of the team.
    version : Optional[str], default: None
        The version of the identifier.
    """

    def __init__(self, dataset_slug: str, team_slug: Optional[str] = None, version: Optional[str] = None):
        self.dataset_slug = dataset_slug
        self.team_slug = team_slug
        self.version = version

    @classmethod
    def parse(cls, identifier: Union[str, "DatasetIdentifier"]) -> "DatasetIdentifier":
        """
        Parses the given identifier and returns the corresponding DatasetIdentifier.

        Parameters
        ----------
        identifier : Union[str, DatasetIdentifier]
            The identifier to be parsed.

        Returns
        -------
        DatasetIdentifier
            The SDK representation of a ``DatasetIdentifier``.

        Raises
        ------
        ValueError
            If the ``identifier`` given is invalid.
        """
        if isinstance(identifier, DatasetIdentifier):
            return identifier

        team_slug, dataset_slug, version = _parse(identifier)
        return cls(dataset_slug=dataset_slug, team_slug=team_slug, version=version)

    def __str__(self):
        output = ""
        if self.team_slug:
            output = f"{self.team_slug}/"
        output = f"{output}{self.dataset_slug}"
        if self.version:
            output = f"{output}:{self.version}"
        return output


def _parse(slug: str) -> Tuple[Optional[str], str, Optional[str]]:
    team: Optional[str] = None
    version: Optional[str] = None

    if not _is_slug_valid(slug):
        raise ValueError(f"Invalid dataset identifier {slug}")

    initial_split = slug.split("/")
    if len(initial_split) == 1:
        dataset = initial_split[0]
    elif len(initial_split) == 2:
        team, dataset = initial_split
    else:
        raise ValueError(f"Invalid dataset identifier {slug}")

    if ":" in dataset:
        dataset, version = dataset.split(":")

    return team, dataset, version


def _is_slug_valid(slug: str) -> bool:
    slug_format = "[\\_a-zA-Z0-9.-]+"
    version_format = "[\\_a-zA-Z0-9.:-]+"
    return re.fullmatch(rf"({slug_format}/)?{slug_format}(:{version_format})?", slug) is not None
