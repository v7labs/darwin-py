from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, validator


class Point(BaseModel):
    x: float
    y: float

class PolygonPath(BaseModel):
    points: List[Point]

class Polygon(BaseModel):
    paths: List[PolygonPath]

class AnnotationBase(BaseModel):
    id: str
    name: str
    properties: Optional[dict] = None
    slot_names: Optional[List[str]] = None

class BoundingBox(BaseModel):
    h: float
    w: float
    x: float
    y: float

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
    
    @validator('bounding_box', always=True)
    def validate_bounding_box(cls, v: Optional[BoundingBox], values: dict) -> BoundingBox:
        if v is None:
            h, w, x, y = 0.0, 0.0, 0.0, 0.0
            for point in values['polygon']['paths']:
                h = max(h, point.y)
                w = max(w, point.x)
                x = min(x, point.x)
                y = min(y, point.y)
            v = BoundingBox(h=h, w=w, x=x, y=y)
        return v

class FrameAnnotation(AnnotationBase):
    frames: List
    interpolated: bool
    interpolate_algorithm: str
    ranges: List[int]


AllowedAnnotation = Union[BoundingBoxAnnotation, EllipseAnnotation, PolygonAnnotation]

class DarwinV2(BaseModel):
    version: Literal["2.0"] = "2.0"
    schema_ref: AnyUrl
    item: dict
    annotations: List[AllowedAnnotation]


class Item(BaseModel):
    name: str
    path: str
    

