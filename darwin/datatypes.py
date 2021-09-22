from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from darwin.path_utils import construct_full_path

Point = Dict[str, float]
BoundingBox = Dict[str, float]
Polygon = List[Point]
ComplexPolygon = List[Polygon]
Node = Dict[str, Any]
EllipseData = Dict[str, Any]
CuboidData = Dict[str, Any]


@dataclass(frozen=True, eq=True)
class AnnotationClass:
    name: str
    annotation_type: str
    annotation_internal_type: Optional[str] = None


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
        return None


@dataclass(frozen=True, eq=True)
class VideoAnnotation:
    annotation_class: AnnotationClass
    frames: Annotation
    keyframes: List[bool]
    segments: List[List[int]]
    interpolated: bool

    def get_data(self, only_keyframes=True, post_processing=None):
        if not post_processing:
            post_processing = lambda annotation, data: data
        return {
            "frames": {
                frame: {
                    **post_processing(
                        self.frames[frame],
                        {self.frames[frame].annotation_class.annotation_type: self.frames[frame].data},
                    ),
                    **{"keyframe": self.keyframes[frame]},
                }
                for frame in self.frames
                if not only_keyframes or self.keyframes[frame]
            },
            "segments": self.segments,
            "interpolated": self.interpolated,
        }


@dataclass
class AnnotationFile:
    path: Path
    filename: str
    annotation_classes: Set[AnnotationClass]
    annotations: List[Annotation]
    is_video: bool = False
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    image_url: Optional[str] = None
    workview_url: Optional[str] = None
    seq: Optional[int] = None
    frame_urls: Optional[List[str]] = None
    remote_path: Optional[str] = None

    @property
    def full_path(self) -> str:
        return construct_full_path(self.remote_path, self.filename)


def make_bounding_box(
    class_name: str, x: float, y: float, w: float, h: float, subs: Optional[List[SubAnnotation]] = None
):
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
        subs or [],
    )


def make_tag(class_name: str, subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "tag"), {}, subs or [])


def make_polygon(class_name: str, point_path: List[Point], subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "polygon"), {"path": point_path}, subs or [])


def make_complex_polygon(class_name: str, point_paths: List[List[Point]], subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "complex_polygon", "polygon"), {"paths": point_paths}, subs or [])


def make_keypoint(class_name: str, x: float, y: float, subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "keypoint"), {"x": x, "y": y}, subs or [])


def make_line(class_name: str, path: List[Point], subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "line"), {"path": path}, subs or [])


def make_skeleton(class_name: str, nodes: List[Node], subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "skeleton"), {"nodes": nodes}, subs or [])


def make_ellipse(class_name: str, parameters: EllipseData, subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "ellipse"), parameters, subs or [])


def make_cuboid(class_name: str, cuboid: CuboidData, subs: Optional[List[SubAnnotation]] = None):
    return Annotation(AnnotationClass(class_name, "cuboid"), cuboid, subs or [])


def make_instance_id(value):
    return SubAnnotation("instance_id", value)


def make_attributes(attributes):
    return SubAnnotation("attributes", attributes)


def make_text(text):
    return SubAnnotation("text", text)


def make_keyframe(annotation, idx):
    return {"idx": idx, "annotation": annotation}


def make_video(keyframes, start, end):
    first_annotation = keyframes[0]["annotation"]
    return Annotation(
        first_annotation.annotation_class,
        {
            "frames": {
                keyframe["idx"]: {
                    **{first_annotation.annotation_class.annotation_type: keyframe["annotation"].data},
                    **{"keyframe": True},
                }
                for keyframe in keyframes
            },
            "interpolated": False,
            "segments": [[start, end]],
        },
    )


def make_video_annotation(frames, keyframes, segments, interpolated):
    first_annotation = list(frames.values())[0]
    if not all(frame.annotation_class.name == first_annotation.annotation_class.name for frame in frames.values()):
        raise ValueError("invalid argument to make_video_annotation")

    return VideoAnnotation(first_annotation.annotation_class, frames, keyframes, segments, interpolated)
