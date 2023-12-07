from typing import List, Literal, Optional, Union

from pydantic import AnyUrl, validator

from darwin.future.pydantic_base import DefaultDarwin


class Point(DefaultDarwin):
    x: float
    y: float

class Polygon(DefaultDarwin):
    paths: list[list[Point]]

class AnnotationBase(DefaultDarwin):
    id: str
    name: str
    properties: Optional[dict] = None
    slot_names: Optional[List[str]] = None

class BoundingBox(DefaultDarwin):
    h: float
    w: float
    x: float
    y: float

class BoundingBoxAnnotation(AnnotationBase):
    bouding_box: BoundingBox

class Ellipse(DefaultDarwin):
    center: Point
    radius: Point
    angle: float

class EllipseAnnotation(AnnotationBase):
    ellipse: Ellipse

class PolygonAnnotation(AnnotationBase):
    polygon: Polygon
    bounding_box: Optional[BoundingBox] = None
    
    @validator('bounding_box', always=True)
    def validate_bounding_box(cls, v: Optional[BoundingBox], values: dict) -> BoundingBox:
        if v is None:
            raise NotImplementedError("TODO: Implement bounding box from polygon")
        return v

class FrameAnnotation(AnnotationBase):
    frames: list
    interpolated: bool
    interpolate_algorithm: str
    ranges: list[int]


AllowedAnnotation = Union[BoundingBoxAnnotation, FrameAnnotation, EllipseAnnotation, PolygonAnnotation]

class DarwinV2(DefaultDarwin):
    version: Literal["2.0"] = "2.0"
    schema_ref: AnyUrl
    item: dict
    annotations: List[AllowedAnnotation]


class Item(DefaultDarwin):
    name: str
    path: str
    