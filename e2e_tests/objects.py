from collections import namedtuple
from dataclasses import dataclass
from typing import List, Literal, Optional
from uuid import UUID

from darwin.datatypes import JSONType

ConfigValues = namedtuple("ConfigValues", ["server", "api_key", "team_slug"])


@dataclass
class E2EAnnotation:
    annotation_data: JSONType


@dataclass
class E2EAnnotationClass:
    name: str
    slug: str
    type: Literal["bbox", "polygon"]
    id: int


@dataclass
class E2EItem(Exception):
    name: str
    id: UUID
    path: str
    file_name: str
    slot_name: str
    annotations: List[E2EAnnotation]

    def add_annotation(self, annotation: E2EAnnotation) -> None:
        self.annotations.append(annotation)


@dataclass
class E2EDataset:
    id: int
    name: str
    slug: str
    items: List[E2EItem]
    directory: Optional[str] = None
    
    def __init__(self, id: int, name: str, slug: Optional[str], directory: Optional[str]=None) -> None:
        self.id = id
        self.name = name
        self.slug = slug or name.lower().replace(" ", "_")
        self.items = []
        self.directory = directory

    def add_item(self, item: E2EItem) -> None:
        self.items.append(item)


@dataclass
class E2ETestRunInfo:
    prefix: str
    datasets: List[E2EDataset]
