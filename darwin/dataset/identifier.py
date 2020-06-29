from typing import Optional


class DatasetIdentifier:
    def __init__(self, dataset_slug: str, team_slug: Optional[str] = None, version: Optional[str] = None):
        self.dataset_slug = dataset_slug
        self.team_slug = team_slug
        self.version = version

    @classmethod
    def parse(cls, identifier: str):
        team_slug, dataset_slug, version = parse(identifier)
        return cls(dataset_slug=dataset_slug, team_slug=team_slug, version=version)

    def __str__(self):
        output = ""
        if self.team_slug:
            output = f"{self.team_slug}/"
        output = f"{output}{self.dataset_slug}"
        if self.version:
            output = f"{output}:{self.version}"
        return output


def parse(slug: str):
    try:
        if "/" in slug:
            team, slug = slug.split("/")
        else:
            team = None

        if ":" in slug:
            dataset, version = slug.split(":")
        else:
            dataset = slug
            version = None
        return team, dataset, version
    except ValueError as e:
        raise type(e)(f"Invalid dataset identifier {slug}")
