# class DatasetIdentifier:
#     def __init__(self, slug):
#         self.team_slug, self.dataset_slug, self.version = parse(slug)
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
