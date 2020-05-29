from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Set


@dataclass(frozen=True, eq=True)
class AnnotationClass:
    name: str
    annotation_type: str


@dataclass(frozen=True, eq=True)
class SubAnnotation:
    annotation_type: str
    data: Any


@dataclass(frozen=True, eq=True)
class Annotation:
    annotation_class: AnnotationClass
    data: Any
    subs: List[SubAnnotation] = field(default_factory=list)

    def get_sub(self, annotation_type: str) -> Optional[SubAnnotation]:
        for sub in self.subs:
            if sub.annotation_type == annotation_type:
                return sub


@dataclass
class AnnotationFile:
    path: Path
    filename: str
    annotation_classes: Set[AnnotationClass]
    annotations: List[Annotation]
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    image_url: Optional[str] = None
    workview_url: Optional[str] = None
    seq: Optional[int] = None


def make_bounding_box(class_name, x, y, w, h):
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
    )


def make_tag(class_name):
    return Annotation(AnnotationClass(class_name, "tag"), {})


def make_polygon(class_name, point_path):
    return Annotation(AnnotationClass(class_name, "polygon"), {"path": point_path})


def make_instance_id(value):
    return SubAnnotation("instance_id", value)


def make_attributes(attributes):
    return SubAnnotation("attributes", attributes)


def make_text(text):
    return SubAnnotation("text", text)
