from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from darwin.path_utils import construct_full_path

Point = Dict[str, float]
BoundingBox = Dict[str, float]
Polygon = List[Point]
ComplexPolygon = List[Polygon]
Node = Dict[str, Any]
EllipseData = Dict[str, Any]
CuboidData = Dict[str, Any]
KeyFrame = Dict[str, Any]
Segment = List[int]

DarwinVersionNumber = Tuple[int, int, int]

PathLike = Union[str, Path]
ErrorHandler = Callable[[int, str], None]


@dataclass
class Team:
    """Definition of a V7 team"""

    default: bool
    slug: str
    datasets_dir: str
    api_key: str
    selected: bool = False


@dataclass(frozen=True)
class Feature:
    """Structured payload of a Feature record on V7 Darwin"""

    name: str
    enabled: bool


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
    frames: Dict[int, Any]
    keyframes: Dict[int, bool]
    segments: List[Segment]
    interpolated: bool

    def get_data(
        self, only_keyframes: bool = True, post_processing: Callable[[Annotation, Any], Any] = None
    ) -> Dict[str, Any]:
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
    annotations: List[Union[VideoAnnotation, Annotation]]
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
) -> Annotation:
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
        subs or [],
    )


def make_tag(class_name: str, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    return Annotation(AnnotationClass(class_name, "tag"), {}, subs or [])


def make_polygon(
    class_name: str,
    point_path: List[Point],
    bounding_box: Optional[Dict] = None,
    subs: Optional[List[SubAnnotation]] = None,
) -> Annotation:
    return Annotation(
        AnnotationClass(class_name, "polygon"),
        _maybe_add_bounding_box_data({"path": point_path}, bounding_box),
        subs or [],
    )


def make_complex_polygon(
    class_name: str,
    point_paths: List[List[Point]],
    bounding_box: Optional[Dict] = None,
    subs: Optional[List[SubAnnotation]] = None,
) -> Annotation:
    return Annotation(
        AnnotationClass(class_name, "complex_polygon", "polygon"),
        _maybe_add_bounding_box_data({"paths": point_paths}, bounding_box),
        subs or [],
    )


def make_keypoint(class_name: str, x: float, y: float, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    return Annotation(AnnotationClass(class_name, "keypoint"), {"x": x, "y": y}, subs or [])


def make_line(class_name: str, path: List[Point], subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    return Annotation(AnnotationClass(class_name, "line"), {"path": path}, subs or [])


def make_skeleton(class_name: str, nodes: List[Node], subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    return Annotation(AnnotationClass(class_name, "skeleton"), {"nodes": nodes}, subs or [])


def make_ellipse(class_name: str, parameters: EllipseData, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    return Annotation(AnnotationClass(class_name, "ellipse"), parameters, subs or [])


def make_cuboid(class_name: str, cuboid: CuboidData, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    return Annotation(AnnotationClass(class_name, "cuboid"), cuboid, subs or [])


def make_instance_id(value: int) -> SubAnnotation:
    return SubAnnotation("instance_id", value)


def make_attributes(attributes: Any) -> SubAnnotation:
    return SubAnnotation("attributes", attributes)


def make_text(text: str) -> SubAnnotation:
    return SubAnnotation("text", text)


def make_keyframe(annotation: Annotation, idx: int) -> KeyFrame:
    return {"idx": idx, "annotation": annotation}


def make_video(keyframes: List[KeyFrame], start, end) -> Annotation:
    first_annotation: Annotation = keyframes[0]["annotation"]
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


def make_video_annotation(
    frames: Dict[int, Any], keyframes: Dict[int, bool], segments: List[Segment], interpolated: bool
) -> VideoAnnotation:
    first_annotation: Annotation = list(frames.values())[0]
    if not all(frame.annotation_class.name == first_annotation.annotation_class.name for frame in frames.values()):
        raise ValueError("invalid argument to make_video_annotation")

    return VideoAnnotation(first_annotation.annotation_class, frames, keyframes, segments, interpolated)


def _maybe_add_bounding_box_data(data: Dict[str, Any], bounding_box: Optional[Dict]) -> Dict[str, Any]:
    if bounding_box:
        data["bounding_box"] = {
            "x": bounding_box["x"],
            "y": bounding_box["y"],
            "w": bounding_box["w"],
            "h": bounding_box["h"],
        }
    return data


ExportParser = Callable[[Iterator[AnnotationFile], Path], None]
ExporterFormat = Tuple[str, ExportParser]

ImportParser = Callable[[Path], Union[List[AnnotationFile], AnnotationFile, None]]
ImporterFormat = Tuple[str, ImportParser]
