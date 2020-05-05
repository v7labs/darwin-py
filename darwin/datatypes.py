from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


@dataclass(frozen=True, eq=True)
class AnnotationClass:
    name: str
    annotation_type: str


@dataclass(frozen=True, eq=True)
class Annotation:
    annotation_class: AnnotationClass
    data: any


@dataclass
class AnnotationFile:
    path: Path
    filename: str
    annotation_classes: Set[AnnotationClass]
    annotations: List[Annotation]


def make_bounding_box(class_name, x, y, w, h):
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
    )


def make_tag(class_name):
    return Annotation(AnnotationClass(class_name, "tag"), {})
