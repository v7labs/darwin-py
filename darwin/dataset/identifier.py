from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DatasetIdentifier:
    identifier: str
    dataset_slug: str = field(init=False)
    team_slug: Optional[str] = field(init=False)
    version: Optional[str] = field(init=False)

    def __post_init__(self):
        self.team_slug, self.dataset_slug, self.version = parse(self.identifier)

    def __str__(self):
        output = ""
        if self.team_slug:
            output = f"{self.team_slug}/"
        output = f"{output}{self.dataset_slug}"
        if self.version:
            output = f"{output}:{self.version}"
        return output

    @classmethod
    def from_slug(cls, dataset_slug: str, team_slug: str = None):
        if dataset_slug is None:
            raise ValueError(f"Dataset slug is {dataset_slug}. Invalid value.")
        if team_slug is not None:
            identifier = team_slug + "/"
        else:
            identifier = ""
        identifier += dataset_slug
        return cls(identifier=identifier)

def parse(slug: str):
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
