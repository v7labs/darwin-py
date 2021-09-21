from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Image:
    width: int
    height: int
    original_filename: str
    filename: str
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    path: Optional[str] = None
    workview_url: Optional[str] = None


@dataclass
class BoundingBox:
    h: float
    w: float
    x: float
    y: float


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Polygon:
    path: List[Point]


@dataclass
class Annotation:
    name: str


@dataclass
class PolygonAnnotation(Annotation):
    bounding_box: BoundingBox
    polygon: Polygon


@dataclass
class TagAnnotation(Annotation):
    tag: Dict = field(default_factory=dict)


@dataclass
class BoundingBoxAnnotation(Annotation):
    bounding_box: BoundingBox


@dataclass
class AnnotationFile:
    dataset: str
    image: Image
    annotations: List[Annotation]
