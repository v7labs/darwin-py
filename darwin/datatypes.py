from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

Point = Dict[str, float]
BoundingBox = Dict[str, float]
Polygon = List[Point]
ComplexPolygon = List[Polygon]


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


@dataclass(frozen=True, eq=True)
class VideoAnnotation:
    annotation_class: AnnotationClass
    frames: Annotation
    keyframes: List[bool]
    segments: List[List[int]]
    interpolated: bool

    def get_frame(self, frame_index: int):
        return frames[frame_index]

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


def make_bounding_box(class_name, x, y, w, h):
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
    )


def make_tag(class_name):
    return Annotation(AnnotationClass(class_name, "tag"), {})


def make_polygon(class_name, point_path):
    return Annotation(AnnotationClass(class_name, "polygon"), {"path": point_path})


def make_complex_polygon(class_name, point_paths):
    return Annotation(AnnotationClass(class_name, "complex_polygon", "polygon"), {"paths": point_paths})


def make_keypoint(class_name, x, y):
    return Annotation(AnnotationClass(class_name, "keypoint"), {"x": x, "y": y})


def make_line(class_name, path):
    return Annotation(AnnotationClass(class_name, "line"), {"path": path})


def make_skeleton(class_name, nodes):
    return Annotation(AnnotationClass(class_name, "skeleton"), {"nodes": nodes})


def make_ellipse(class_name, parameters):
    return Annotation(AnnotationClass(class_name, "ellipse"), parameters)


def make_cuboid(class_name, cuboid):
    return Annotation(AnnotationClass(class_name, "cuboid"), cuboid)


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
