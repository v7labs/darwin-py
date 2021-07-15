from typing import Optional, Tuple


class DatasetIdentifier:
    def __init__(self, dataset_slug: str, team_slug: Optional[str] = None, version: Optional[str] = None):
        self.dataset_slug = dataset_slug
        self.team_slug = team_slug
        self.version = version

    @classmethod
    def parse(cls, identifier: str):
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
    dataset: str = slug

    try:
        if "/" in slug:
            team, slug = slug.split("/")

        if ":" in slug:
            dataset, version = slug.split(":")

        return team, dataset, version
    except ValueError as e:
        raise type(e)(f"Invalid dataset identifier {slug}")
