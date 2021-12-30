from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

from darwin.path_utils import construct_full_path

Point = Dict[str, float]
BoundingBox = Dict[str, float]
Polygon = List[Point]
ComplexPolygon = List[Polygon]
Node = Dict[str, Any]
EllipseData = Dict[str, Union[float, Point]]
CuboidData = Dict[str, Dict[str, float]]
KeyFrame = Dict[str, Any]
Segment = List[int]

DarwinVersionNumber = Tuple[int, int, int]

PathLike = Union[str, Path]
ErrorHandler = Callable[[int, str], None]


@dataclass
class Team:
    """
    Definition of a V7 team.

    Attributes
    ----------
    default: bool
        If this is the default Team or not.
    slug: str
        This team's slug.
    datasets_dir: str
        The path to the directory of all datasets this teams contains.
    api_key: str
        The API key used to authenticate for this Team.
    selected: bool, default: False
        If this is the currently active Team. Defaults to ``False``.
    """

    default: bool
    slug: str
    datasets_dir: str
    api_key: str
    selected: bool = False


@dataclass(frozen=True)
class Feature:
    """
    Structured payload of a Feature record on V7 Darwin.

    Attributes
    ----------
    name: str
        The name of this ``Feature``.
    enabled: bool
        Whether or not this ``Feature`` is enabled. Disabled ``Feature``s do nothing, as if they
        didn't exist.
    """

    name: str
    enabled: bool


@dataclass(frozen=True, eq=True)
class AnnotationClass:
    """
    Represents an AnnocationClass from an Annotation.

    Attributes
    ----------
    name: str
        The name of this ``AnnotationClass``.
    annotation_type: str
        The type of this ``AnnotationClass``.
    annotation_internal_type: Optional[str], default: None
        The V7 internal type of this ``AnnotationClass``. This is mostly used to convert from types
        that are known in the outside world by a given name, but then are known inside V7's lingo
        by another.
    """

    name: str
    annotation_type: str
    annotation_internal_type: Optional[str] = None


@dataclass(frozen=True, eq=True)
class SubAnnotation:
    """
    Represents a subannotation that belongs to an AnnotationClass.

    Attributes
    ----------
    annotation_type: str
        The type of this ``SubAnnotation``.
    data: Any
        Any external data, in any format, relevant to this ``SubAnnotation``. Used for compatibility
        purposes with external formats.
    """

    annotation_type: str
    data: Any


@dataclass(frozen=True, eq=True)
class Annotation:
    """
    Represents an Annotation from an Image/Video.

    Attributes
    ----------
    annotation_class: AnnotationClass
        The ``AnnotationClass`` from this ``Annotation``.
    data: Any
        Any external data, in any format, relevant to this ``Annotation``. Used for compatibility
        purposes with external formats.
    subs: List[SubAnnotation]
        List of ``SubAnnotations`` belonging to this ``Annotation``.
    """

    annotation_class: AnnotationClass
    data: Any
    subs: List[SubAnnotation] = field(default_factory=list)

    def get_sub(self, annotation_type: str) -> Optional[SubAnnotation]:
        """
        Returns the first SubAnnotation that matches the given type.

        Parameters
        ----------
        annotation_type: str
            The type of the subannotation.

        Returns
        -------
        Optional[SubAnnotation]
            A SubAnnotation found, or `None` if none was found.
        """
        for sub in self.subs:
            if sub.annotation_type == annotation_type:
                return sub
        return None


@dataclass(frozen=True, eq=True)
class VideoAnnotation:
    """
    Represents an Annotation that belongs to a Video.

    Attributes
    ----------
    annotation_class: AnnotationClass
        The ``AnnotationClass`` from this ``VideoAnnotation``.
    frames: Dict[int, Any]
        A dictionary of frames for this ``VideoAnnotation``.
    keyframes: Dict[int, bool]
        The keyframes for this ``VideoAnnotation``. Keyframes are a selection of frames from the
        ``frames`` attribute.
    segments: List[Segment]
        A list of ``Segment``'s.
    interpolated: bool
        Whehter this ``VideoAnnotation`` is interpolated or not.
    """

    annotation_class: AnnotationClass
    frames: Dict[int, Any]
    keyframes: Dict[int, bool]
    segments: List[Segment]
    interpolated: bool

    def get_data(
        self, only_keyframes: bool = True, post_processing: Optional[Callable[[Annotation, Any], Any]] = None
    ) -> Dict[str, Any]:
        """
        Return the post-processed frames and the additional information from this
        ``VideoAnnotation`` in a dictionary with the format:

        .. code-block:: python
            {
                "frames": {
                    # Post-Processed Frames here
                },
                "segments": [
                    # Segments here
                ]
                "interpolated": True
            }

        Parameters
        ----------
        only_keyframes: bool, default: True
            Whether or not to return only the keyframes. Defaults to ``True``.
        post_processing: Optional[Callable[[Annotation, Any], Any]], default: None
            If given, it processes each frame through the given ``Callabale`` before adding it to the
            returned dictionary. Defaults to ``None``.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the processed frames, the segments of this ``VideoAnnotation``
            and whether or not it is interpolated.
        """
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
    """
    Represents a file containing annotations. Mostly useful when trying to import or export
    annotations to/from darwin V7.

    Attributes
    ----------
    path: Path
        Path to the file.
    filename: str
        Name of the file containing the annotations.
    annotation_classes: Set[AnnotationClass]
        ``Set`` of all ``AnnotationClass``es this file contains. Used as a way to know in advance
        which ``AnnotationClass``es this file has without having to go through the list of
        annotations.
    annotations: Union[List[VideoAnnotation], List[Annotation]]
        List of ``VideoAnnotation``s or ``Annotation``s.
    is_video: bool, default: False
        Whether the annotations in the ``annotations`` attribute are ``VideoAnnotation`` or not.
        Defaults to ``False``.
    image_width: Optional[int], default:  None
        Width of the image in this annotation. Defaults to ``None``.
    image_height: Optional[int], default:  None
        Height of the image in this annotation. Defaults to ``None``.
    image_url: Optional[str], default:  None
        URL of the image in this annotation. Defaults to ``None``.
    workview_url: Optional[str], default:  None
        URL of the workview for this annotation. Defaults to ``None``.
    seq: Optional[int], default:  None
        Sequence for this annotation. Defaults to ``None``.
    frame_urls: Optional[List[str]], default:  None
        URLs for the frames this ``AnnotationFile`` has. Defautls to ``None``.
    remote_path: Optional[str], default:  None
        Remote path for this Annoataion file in V7's darwin. Defaults to ``None``.
    """

    path: Path
    filename: str
    annotation_classes: Set[AnnotationClass]
    annotations: Union[List[VideoAnnotation], List[Annotation]]
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
        """
        Returns the absolute path of this file.

        Returns
        -------
        str
            The absolute path of the file.
        """
        return construct_full_path(self.remote_path, self.filename)


def make_bounding_box(
    class_name: str, x: float, y: float, w: float, h: float, subs: Optional[List[SubAnnotation]] = None
) -> Annotation:
    """
    Creates and returns a bounding box annotation. ``x``, ``y``, ``w`` and ``h`` are rounded to 3
    decimal places when creating the annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    x: float
        The top left ``x`` value where the bounding box will start.
    y: float
        The top left ``y`` value where the bounding box will start.
    w: float
        The width of the bounding box.
    h: float
        The height of the bounding box.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A bounding box ``Annotation``.
    """
    return Annotation(
        AnnotationClass(class_name, "bounding_box"),
        {"x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3)},
        subs or [],
    )


def make_tag(class_name: str, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    """
    Creates and returns a tag annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A tag ``Annotation``.
    """
    return Annotation(AnnotationClass(class_name, "tag"), {}, subs or [])


def make_polygon(
    class_name: str,
    point_path: List[Point],
    bounding_box: Optional[Dict] = None,
    subs: Optional[List[SubAnnotation]] = None,
) -> Annotation:
    """
    Creates and returns a polygon annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    point_path: List[Point]
        A list of points that comprises the polygon. The list should have a format simillar to:

        .. code-block:: python
            [
                {"x": 1, "y": 0},
                {"x": 2, "y": 1}
            ]

    bounding_box: Optional[Dict], default: None
        The bounding box that encompasses the polyong. Defaults to ``None``.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A polygon ``Annotation``.
    """
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
    """
    Creates and returns a conplex polygon annotation. Complex polygons are those who have holes 
    and/or disform shapes.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    point_paths: List[List[Point]]
        A list of lists points that comprises the complex polygon. This is needed as a complex 
        polygon can be effectively seen as a sum of multiple simple polygons. The list should have 
        a format simillar to:

        .. code-block:: python
            [
                [
                    {"x": 1, "y": 0},
                    {"x": 2, "y": 1}
                ],
                [
                    {"x": 3, "y": 4},
                    {"x": 5, "y": 6}
                ]
                # ... and so on ...
            ]

    bounding_box: Optional[Dict], default: None
        The bounding box that encompasses the polyong. Defaults to ``None``.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A complex polygon ``Annotation``.
    """
    return Annotation(
        AnnotationClass(class_name, "complex_polygon", "polygon"),
        _maybe_add_bounding_box_data({"paths": point_paths}, bounding_box),
        subs or [],
    )


def make_keypoint(class_name: str, x: float, y: float, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    """
    Creates and returns a keypoint, aka point, annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    x: float
        The ``x`` value of the point.
    y: float
        The ``y`` value of the point.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A point ``Annotation``.
    """
    return Annotation(AnnotationClass(class_name, "keypoint"), {"x": x, "y": y}, subs or [])


def make_line(class_name: str, path: List[Point], subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    """
    Creates and returns a line annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    point_path: List[Point]
        A list of points that comprises the polygon. The list should have a format simillar to:

        .. code-block:: python
            [
                {"x": 1, "y": 0},
                {"x": 2, "y": 1}
            ]

    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A line ``Annotation``.
    """
    return Annotation(AnnotationClass(class_name, "line"), {"path": path}, subs or [])


def make_skeleton(class_name: str, nodes: List[Node], subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    """
    Creates and returns a skeleton annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    nodes: List[Node]
        List of ``Node``s that comprise the skeleton. Each Node will have a format simillar to:

        .. code-block:: python
            {
                "name": "1",
                "occluded": false,
                "x": 172.78,
                "y": 939.81
            }

    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A skeleton ``Annotation``.
    """
    return Annotation(AnnotationClass(class_name, "skeleton"), {"nodes": nodes}, subs or [])


def make_ellipse(class_name: str, parameters: EllipseData, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    """
    Creates and returns an Ellipse annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    parameters: EllipseData
        The data needed to build an Ellipse. This data must be a dictionary with a format simillar 
        to:

        .. code-block:: javascript
            {
                "angle": 0.57,
                "center": {
                    "x": 2745.69,
                    "y": 2307.46
                },
                "radius": {
                    "x": 467.02,
                    "y": 410.82
                }
            }

        Where:
        
        - ``angle: float`` is the orientation angle of the ellipse.
        - ``center: Point`` is the center point of the ellipse.
        - ``radius: Point`` is the width and height of the elipse, where ``x`` represents the width 
        and ``y`` represents height.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        An ellipse ``Annotation``. 
    """
    return Annotation(AnnotationClass(class_name, "ellipse"), parameters, subs or [])


def make_cuboid(class_name: str, cuboid: CuboidData, subs: Optional[List[SubAnnotation]] = None) -> Annotation:
    """
    Creates and returns a Cuboid annotation.

    Parameters
    ----------
    class_name: str
        The name of the class for this ``Annotation``.
    parameters: CuboidData
        The data needed to build a .Cuboid This data must be a dictionary with a format simillar 
        to:

        .. code-block:: javascript
            {
                "back": {"h": 381.25, "w": 1101.81, "x": 1826.19, "y": 1841.44},
                "front": {"h": 575.69, "w": 1281.0, "x": 1742.31, "y": 1727.06}
            }

        Where:
        
        - ``back: Dict[str, float]`` is a dictionary containing the ``x`` and ``y`` of the top
        left corner Point, together with the width ``w`` and height ``h`` to form the back box.
        - ``front: Dict[str, float]`` is a dictionary containing the ``x`` and ``y`` of the top
        left corner Point, together with the width ``w`` and height ``h`` to form the front box.
    subs: Optional[List[SubAnnotation]], default: None
        List of ``SubAnnotation``s for this ``Annotation``. Defaults to ``None``.

    Returns
    -------
    Annotation
        A cuboid ``Annotation``. 
    """
    return Annotation(AnnotationClass(class_name, "cuboid"), cuboid, subs or [])


def make_instance_id(value: int) -> SubAnnotation:
    """
    Creates and returns an instance id sub-annotation.

    Parameters
    ----------
    value: int
        The value of this instance's id.
    

    Returns
    -------
    SubAnnotation
        An instance id ``SubAnnotation``. 
    """
    return SubAnnotation("instance_id", value)


def make_attributes(attributes: List[str]) -> SubAnnotation:
    """
    Creates and returns an attributes sub-annotation.

    Parameters
    ----------
    value: List[str]
        A list of attributes. Example: ``["orange", "big"]``.
    
    Returns
    -------
    SubAnnotation
        An attributes ``SubAnnotation``. 
    """
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

ImportParser = Callable[[Path], Union[List[AnnotationFile], AnnotationFile, None]]
