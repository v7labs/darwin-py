from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, validator

from darwin.future.data_objects.properties import SelectedProperty


class Point(BaseModel):
    x: float
    y: float

    def __add__(self, other: Point) -> Point:
        return Point(x=self.x + other.x, y=self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(x=self.x - other.x, y=self.y - other.y)


PolygonPath = List[Point]


class Polygon(BaseModel):
    paths: List[PolygonPath]

    def bounding_box(self) -> BoundingBox:
        h, w, x, y = 0.0, 0.0, 0.0, 0.0
        for polygon_path in self.paths:
            for point in polygon_path:
                h = max(h, point.y)
                w = max(w, point.x)
                x = min(x, point.x)
                y = min(y, point.y)
        return BoundingBox(h=h, w=w, x=x, y=y)

    @property
    def is_complex(self) -> bool:
        return len(self.paths) > 1

    @property
    def center(self) -> Point:
        return self.bounding_box().center


class AnnotationBase(BaseModel):
    id: str
    name: str
    properties: Optional[SelectedProperty] = None
    slot_names: Optional[List[str]] = None

    @validator("id", always=True)
    def validate_id_is_UUID(cls, v: str) -> str:
        assert len(v) == 36
        assert "-" in v
        return v


class BoundingBox(BaseModel):
    h: float
    w: float
    x: float
    y: float

    @property
    def center(self) -> Point:
        return Point(x=self.x + self.w / 2, y=self.y + self.h / 2)


class BoundingBoxAnnotation(AnnotationBase):
    bounding_box: BoundingBox


class Ellipse(BaseModel):
    center: Point
    radius: Point
    angle: float


class EllipseAnnotation(AnnotationBase):
    ellipse: Ellipse


class PolygonAnnotation(AnnotationBase):
    polygon: Polygon
    bounding_box: Optional[BoundingBox] = None

    @validator("bounding_box", pre=False, always=True)
    def validate_bounding_box(
        cls, v: Optional[BoundingBox], values: dict
    ) -> BoundingBox:
        if v is None:
            assert "polygon" in values
            assert isinstance(values["polygon"], Polygon)
            v = values["polygon"].bounding_box()
        return v


class FrameAnnotation(AnnotationBase):
    frames: List
    interpolated: bool
    interpolate_algorithm: str
    ranges: List[int]


AllowedAnnotation = Union[
    PolygonAnnotation, BoundingBoxAnnotation, EllipseAnnotation, FrameAnnotation
]


class Item(BaseModel):
    name: str
    path: str


class DarwinV2(BaseModel):
    version: Literal["2.0"] = "2.0"
    schema_ref: str
    item: dict
    annotations: List[AllowedAnnotation]

    @validator("schema_ref", always=True)
    def validate_schema_ref(cls, v: str) -> str:
        assert v.startswith("http")
        return v
