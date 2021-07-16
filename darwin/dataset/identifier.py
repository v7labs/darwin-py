import re
from typing import Optional, Tuple, Union


class DatasetIdentifier:
    def __init__(self, dataset_slug: str, team_slug: Optional[str] = None, version: Optional[str] = None):
        self.dataset_slug = dataset_slug
        self.team_slug = team_slug
        self.version = version

    @classmethod
    def parse(cls, identifier: Union[str, "DatasetIdentifier"]) -> "DatasetIdentifier":
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


def _parse(slug: str) -> Tuple[str, str, Optional[str]]:
    version: Optional[str] = None

    if not re.fullmatch(r"[\w\-]+/[\w\-]+(:[\w\.]+)?", slug):
        raise ValueError(f"Invalid dataset identifier {slug}")

    team, dataset = slug.split("/")

    if ":" in dataset:
        dataset, version = dataset.split(":")

    return team, dataset, version
