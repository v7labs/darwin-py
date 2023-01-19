"""
Contains several unrelated utility functions used across the SDK.
"""

import platform
import re
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Union,
    cast,
)

import deprecation
import numpy as np
import orjson as json
import requests
from jsonschema import exceptions, validators
from requests import Response, request
from rich.progress import ProgressType, track
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.config import Config
from darwin.exceptions import (
    AnnotationFileValidationError,
    MissingSchema,
    OutdatedDarwinJSONFormat,
    UnknownAnnotationFileSchema,
    UnsupportedFileType,
)
from darwin.version import __version__

if TYPE_CHECKING:
    from darwin.client import Client


SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpeg", ".jpg", ".jfif", ".tif", ".tiff", ".bmp", ".svs", ".webp"]
SUPPORTED_VIDEO_EXTENSIONS = [
    ".avi",
    ".bpm",
    ".dcm",
    ".mov",
    ".mp4",
    ".pdf",
    ".nii",
    ".nii.gz",
    ".ndpi",
]
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS

_darwin_schema_cache = {}


def is_extension_allowed_by_filename(filename: str) -> bool:
    """
    Returns whether or not the given video or image extension is allowed.

    Parameters
    ----------
    filename : str
        The filename.

    Returns
    -------
    bool
        Whether or not the given extension of the filename is allowed.
    """
    return any([filename.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS])


@deprecation.deprecated(deprecated_in="0.8.4", current_version=__version__)
def is_extension_allowed(extension: str) -> bool:
    """
    Returns whether or not the given extension is allowed.
    @Deprecated. Use is_extension_allowed_by_filename instead, and pass full filename.
    This is due to the fact that some extensions now include multiple dots, e.g. .nii.gz

    Parameters
    ----------
    extension : str
        The extension.

    Returns
    -------
    bool
        Whether or not the given extension is allowed.
    """
    return extension.lower() in SUPPORTED_EXTENSIONS


def is_image_extension_allowed_by_filename(filename: str) -> bool:
    """
    Returns whether or not the given image extension is allowed.

    Parameters
    ----------
    filename : str
        The image extension.

    Returns
    -------
    bool
        Whether or not the given extension is allowed.
    """
    return any([filename.lower().endswith(ext) for ext in SUPPORTED_IMAGE_EXTENSIONS])


@deprecation.deprecated(deprecated_in="0.8.4", current_version=__version__)
def is_image_extension_allowed(extension: str) -> bool:
    """
    Returns whether or not the given image extension is allowed.

    Parameters
    ----------
    extension : str
        The image extension.

    Returns
    -------
    bool
        Whether or not the given extension is allowed.
    """
    return extension.lower() in SUPPORTED_IMAGE_EXTENSIONS


def is_video_extension_allowed_by_filename(extension: str) -> bool:
    """
    Returns whether or not the given image extension is allowed.

    Parameters
    ----------
    extension : str
        The image extension.

    Returns
    -------
    bool
        Whether or not the given extension is allowed.
    """
    return any([extension.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXTENSIONS])


@deprecation.deprecated(deprecated_in="0.8.4", current_version=__version__)
def is_video_extension_allowed(extension: str) -> bool:
    """
    Returns whether or not the given video extension is allowed.

    Parameters
    ----------
    extension : str
        The video extension.

    Returns
    -------
    bool
        Whether or not the given extension is allowed.
    """
    return extension.lower() in SUPPORTED_VIDEO_EXTENSIONS


def urljoin(*parts: str) -> str:
    """
    Take as input an unpacked list of strings and joins them to form an URL.

    Parameters
    ----------
    parts : str
        The list of strings to form the url.

    Returns
    -------
    str
        The url.
    """
    return "/".join(part.strip("/") for part in parts)


def is_project_dir(project_path: Path) -> bool:
    """
    Verifies if the directory is a project from Darwin by inspecting its structure.

    Parameters
    ----------
    project_path : Path
        Directory to examine

    Returns
    -------
    bool
        Is the directory a project from Darwin?
    """
    return (project_path / "releases").exists() and (project_path / "images").exists()


def get_progress_bar(array: List[dt.AnnotationFile], description: Optional[str] = None) -> Iterable[ProgressType]:
    """
    Get a rich a progress bar for the given list of annotation files.

    Parameters
    ----------
    array : List[dt.AnnotationFile]
        The list of annotation files.
    description : Optional[str], default: None
        A description to show above the progress bar.

    Returns
    -------
    Iterable[ProgressType]
        An iterable of ``ProgressType`` to show a progress bar.
    """
    if description:
        return track(array, description=description)
    return track(array)


def prompt(msg: str, default: Optional[str] = None) -> str:
    """
    Prompt the user on a CLI to input a message.

    Parameters
    ----------
    msg : str
        Message to print.
    default : Optional[str], default: None
        Default values which is put between [] when the user is prompted.

    Returns
    -------
    str
        The input from the user or the default value provided as parameter if user does not provide
        one.
    """
    if default:
        msg = f"{msg} [{default}]: "
    else:
        msg = f"{msg}: "
    result = input(msg)
    if not result and default:
        return default
    return result


def find_files(
    files: List[dt.PathLike], *, files_to_exclude: List[dt.PathLike] = [], recursive: bool = True
) -> List[Path]:
    """
    Retrieve a list of all files belonging to supported extensions. The exploration can be made
    recursive and a list of files can be excluded if desired.

    Parameters
    ----------
    files: List[dt.PathLike]
        List of files that will be filtered with the supported file extensions and returned.
    files_to_exclude : List[dt.PathLike]
        List of files to exclude from the search.
    recursive : bool
        Flag for recursive search.

    Returns
    -------
    List[Path]
        List of all files belonging to supported extensions. Can't return None.
    """

    found_files: List[Path] = []
    pattern = "**/*" if recursive else "*"

    for f in files:
        path = Path(f)
        if path.is_dir() == True:
            found_files.extend(
                [
                    path_object
                    for path_object in path.glob(pattern)
                    if is_extension_allowed_by_filename(str(path_object))
                ]
            )
        elif is_extension_allowed_by_filename(str(path)):
            found_files.append(path)
        else:
            raise UnsupportedFileType(path)

    files_to_exclude_full_paths = [str(Path(f)) for f in files_to_exclude]

    return [f for f in found_files if str(f) not in files_to_exclude_full_paths]


def secure_continue_request() -> bool:
    """
    Asks for explicit approval from the user. Empty string not accepted.

    Returns
    -------
    bool
        True if the user wishes to continue, False otherwise.
    """
    return input("Do you want to continue? [y/N] ") in ["Y", "y"]


def persist_client_configuration(
    client: "Client", default_team: Optional[str] = None, config_path: Optional[Path] = None
) -> Config:
    """
    Authenticate user against the server and creates a configuration file for him/her.

    Parameters
    ----------
    client : Client
        Client to take the configurations from.
    default_team : Optional[str], default: None
        The default team for the user.
    config_path : Optional[Path], default: None
        Specifies where to save the configuration file.

    Returns
    -------
    Config
        A configuration object to handle YAML files.
    """
    if not config_path:
        config_path = Path.home() / ".darwin" / "config.yaml"
        config_path.parent.mkdir(exist_ok=True)

    team_config: Optional[dt.Team] = client.config.get_default_team()
    if not team_config:
        raise ValueError("Unable to get default team.")

    config: Config = Config(config_path)
    config.set_team(team=team_config.slug, api_key=team_config.api_key, datasets_dir=team_config.datasets_dir)
    config.set_global(api_endpoint=client.url, base_url=client.base_url, default_team=default_team)

    return config


def _get_local_filename(metadata: Dict[str, Any]) -> str:
    if "original_filename" in metadata:
        return metadata["original_filename"]
    else:
        return metadata["filename"]


def _get_schema(data: dict) -> Optional[dict]:
    version = _parse_version(data)
    schema_url = data.get("schema_ref") or _default_schema(version)
    if not schema_url:
        return None
    if schema_url not in _darwin_schema_cache:
        response = requests.get(schema_url)
        response.raise_for_status()
        schema = response.json()
        _darwin_schema_cache[schema_url] = schema
    return _darwin_schema_cache[schema_url]


def validate_file_against_schema(path: Path) -> List:
    data, _ = load_data_from_file(path)
    return validate_data_against_schema(data)


def validate_data_against_schema(data) -> List:
    try:
        schema = _get_schema(data)
    except requests.exceptions.RequestException as e:
        raise MissingSchema(f"Error retrieving schema from url: {e}")
    if not schema:
        raise MissingSchema("Schema not found")
    validator = validators.Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    return errors


def load_data_from_file(path: Path):
    with path.open() as infile:
        data = json.loads(infile.read())
    version = _parse_version(data)
    return data, version


def parse_darwin_json(path: Path, count: Optional[int]) -> Optional[dt.AnnotationFile]:
    """
    Parses the given JSON file in v7's darwin proprietary format. Works for images, split frame
    videos (treated as images) and playback videos.

    Parameters
    ----------
    path : Path
        Path to the file to parse.
    count : Optional[int]
        Optional count parameter. Used only if the 's image sequence is None.

    Returns
    -------
    Optional[dt.AnnotationFile]
        An AnnotationFile with the information from the parsed JSON file, or None, if there were no
        annotations in the JSON.

    Raises
    ------
    OutdatedDarwinJSONFormat
        If the given darwin video JSON file is missing the 'width' and 'height' keys in the 'image'
        dictionary.
    """

    path = Path(path)

    data, version = load_data_from_file(path)
    if "annotations" not in data:
        return None

    if version.major == 2:
        return _parse_darwin_v2(path, data)
    else:
        if "fps" in data["image"] or "frame_count" in data["image"]:
            return _parse_darwin_video(path, data, count)
        else:
            return _parse_darwin_image(path, data, count)


def _parse_darwin_v2(path: Path, data: Dict[str, Any]) -> dt.AnnotationFile:
    item = data["item"]
    item_source = item.get("source_info", {})
    slots: List[dt.Slot] = list(filter(None, map(_parse_darwin_slot, item.get("slots", []))))
    annotations: List[Union[dt.Annotation, dt.VideoAnnotation]] = _data_to_annotations(data)
    annotation_classes: Set[dt.AnnotationClass] = set([annotation.annotation_class for annotation in annotations])

    if len(slots) == 0:
        annotation_file = dt.AnnotationFile(
            version=_parse_version(data),
            path=path,
            filename=item["name"],
            annotation_classes=annotation_classes,
            annotations=annotations,
            is_video=False,
            image_width=None,
            image_height=None,
            image_url=None,
            image_thumbnail_url=None,
            workview_url=item_source.get("workview_url", None),
            seq=0,
            frame_urls=None,
            remote_path=item["path"],
            slots=slots,
        )
    else:
        slot = slots[0]
        annotation_file = dt.AnnotationFile(
            version=_parse_version(data),
            path=path,
            filename=item["name"],
            annotation_classes=annotation_classes,
            annotations=annotations,
            is_video=slot.frame_urls is not None,
            image_width=slot.width,
            image_height=slot.height,
            image_url=None if len(slot.source_files or []) == 0 else slot.source_files[0]["url"],
            image_thumbnail_url=slot.thumbnail_url,
            workview_url=item_source["workview_url"],
            seq=0,
            frame_urls=slot.frame_urls,
            remote_path=item["path"],
            slots=slots,
        )

    return annotation_file


def _parse_darwin_slot(data: Dict[str, Any]) -> dt.Slot:
    return dt.Slot(
        name=data["slot_name"],
        type=data["type"],
        width=data.get("width"),
        height=data.get("height"),
        source_files=data.get("source_files", []),
        thumbnail_url=data.get("thumbnail_url"),
        frame_count=data.get("frame_count"),
        frame_urls=data.get("frame_urls"),
        fps=data.get("fps"),
        metadata=data.get("metadata"),
    )


def _parse_darwin_image(path: Path, data: Dict[str, Any], count: Optional[int]) -> dt.AnnotationFile:
    annotations: List[Union[dt.Annotation, dt.VideoAnnotation]] = _data_to_annotations(data)
    annotation_classes: Set[dt.AnnotationClass] = set([annotation.annotation_class for annotation in annotations])

    slot = dt.Slot(
        name=None,
        type="image",
        source_files=[{"url": data["image"].get("url"), "file_name": _get_local_filename(data["image"])}],
        thumbnail_url=data["image"].get("thumbnail_url"),
        width=data["image"].get("width"),
        height=data["image"].get("height"),
        metadata=data["image"].get("metadata"),
    )

    annotation_file = dt.AnnotationFile(
        path=path,
        filename=_get_local_filename(data["image"]),
        annotation_classes=annotation_classes,
        annotations=annotations,
        is_video=False,
        image_width=data["image"].get("width"),
        image_height=data["image"].get("height"),
        image_url=data["image"].get("url"),
        workview_url=data["image"].get("workview_url"),
        seq=data["image"].get("seq", count),
        frame_urls=None,
        remote_path=data["image"].get("path", "/"),
        slots=[],
        image_thumbnail_url=data["image"].get("thumbnail_url"),
    )
    annotation_file.slots.append(slot)
    return annotation_file


def _parse_darwin_video(path: Path, data: Dict[str, Any], count: Optional[int]) -> dt.AnnotationFile:
    annotations: List[Union[dt.Annotation, dt.VideoAnnotation]] = _data_to_annotations(data)
    annotation_classes: Set[dt.AnnotationClass] = set([annotation.annotation_class for annotation in annotations])

    if "width" not in data["image"] or "height" not in data["image"]:
        raise OutdatedDarwinJSONFormat("Missing width/height in video, please re-export")

    slot = dt.Slot(
        name=None,
        type="video",
        source_files=[{"url": data["image"].get("url"), "file_name": _get_local_filename(data["image"])}],
        thumbnail_url=data["image"].get("thumbnail_url"),
        width=data["image"].get("width"),
        height=data["image"].get("height"),
        frame_count=data["image"].get("frame_count"),
        frame_urls=data["image"].get("frame_urls"),
        fps=data["image"].get("fps"),
        metadata=data["image"].get("metadata"),
    )
    annotation_file = dt.AnnotationFile(
        path=path,
        filename=_get_local_filename(data["image"]),
        annotation_classes=annotation_classes,
        annotations=annotations,
        is_video=True,
        image_width=data["image"].get("width"),
        image_height=data["image"].get("height"),
        image_url=data["image"].get("url"),
        workview_url=data["image"].get("workview_url"),
        seq=data["image"].get("seq", count),
        frame_urls=data["image"].get("frame_urls"),
        remote_path=data["image"].get("path", "/"),
        slots=[],
        image_thumbnail_url=data["image"].get("thumbnail_url"),
    )
    annotation_file.slots.append(slot)

    return annotation_file


def _parse_darwin_annotation(annotation: Dict[str, Any]) -> Optional[dt.Annotation]:
    slot_names = parse_slot_names(annotation)
    name: str = annotation["name"]
    main_annotation: Optional[dt.Annotation] = None

    # Darwin JSON 2.0 representation of complex polygons
    if "polygon" in annotation and "paths" in annotation["polygon"] and len(annotation["polygon"]["paths"]) > 1:
        bounding_box = annotation.get("bounding_box")
        paths = annotation["polygon"]["paths"]
        main_annotation = dt.make_complex_polygon(name, paths, bounding_box, slot_names=slot_names)
    # Darwin JSON 2.0 representation of simple polygons
    elif "polygon" in annotation and "paths" in annotation["polygon"] and len(annotation["polygon"]["paths"]) == 1:
        bounding_box = annotation.get("bounding_box")
        paths = annotation["polygon"]["paths"]
        main_annotation = dt.make_polygon(name, paths[0], bounding_box, slot_names=slot_names)
    # Darwin JSON 1.0 representation of complex and simple polygons
    elif "polygon" in annotation:
        bounding_box = annotation.get("bounding_box")
        if "additional_paths" in annotation["polygon"]:
            paths = [annotation["polygon"]["path"]] + annotation["polygon"]["additional_paths"]
            main_annotation = dt.make_complex_polygon(name, paths, bounding_box, slot_names=slot_names)
        else:
            main_annotation = dt.make_polygon(name, annotation["polygon"]["path"], bounding_box, slot_names=slot_names)
    # Darwin JSON 1.0 representation of complex polygons
    elif "complex_polygon" in annotation:
        bounding_box = annotation.get("bounding_box")
        if isinstance(annotation["complex_polygon"]["path"][0], list):
            paths = annotation["complex_polygon"]["path"]
        else:
            paths = [annotation["complex_polygon"]["path"]]

        if "additional_paths" in annotation["complex_polygon"]:
            paths.extend(annotation["complex_polygon"]["additional_paths"])

        main_annotation = dt.make_complex_polygon(name, paths, bounding_box, slot_names=slot_names)
    elif "bounding_box" in annotation:
        bounding_box = annotation["bounding_box"]
        main_annotation = dt.make_bounding_box(
            name, bounding_box["x"], bounding_box["y"], bounding_box["w"], bounding_box["h"], slot_names=slot_names
        )
    elif "tag" in annotation:
        main_annotation = dt.make_tag(name, slot_names=slot_names)
    elif "line" in annotation:
        main_annotation = dt.make_line(name, annotation["line"]["path"], slot_names=slot_names)
    elif "keypoint" in annotation:
        main_annotation = dt.make_keypoint(
            name, annotation["keypoint"]["x"], annotation["keypoint"]["y"], slot_names=slot_names
        )
    elif "ellipse" in annotation:
        main_annotation = dt.make_ellipse(name, annotation["ellipse"], slot_names=slot_names)
    elif "cuboid" in annotation:
        main_annotation = dt.make_cuboid(name, annotation["cuboid"], slot_names=slot_names)
    elif "skeleton" in annotation:
        main_annotation = dt.make_skeleton(name, annotation["skeleton"]["nodes"], slot_names=slot_names)
    elif "table" in annotation:
        main_annotation = dt.make_table(
            name, annotation["table"]["bounding_box"], annotation["table"]["cells"], slot_names=slot_names
        )
    elif "string" in annotation:
        main_annotation = dt.make_string(name, annotation["string"]["sources"], slot_names=slot_names)
    elif "graph" in annotation:
        main_annotation = dt.make_graph(
            name, annotation["graph"]["nodes"], annotation["graph"]["edges"], slot_names=slot_names
        )

    if not main_annotation:
        print(f"[WARNING] Unsupported annotation type: '{annotation.keys()}'")
        return None

    if "instance_id" in annotation:
        main_annotation.subs.append(dt.make_instance_id(annotation["instance_id"]["value"]))
    if "attributes" in annotation:
        main_annotation.subs.append(dt.make_attributes(annotation["attributes"]))
    if "text" in annotation:
        main_annotation.subs.append(dt.make_text(annotation["text"]["text"]))
    if "inference" in annotation:
        main_annotation.subs.append(dt.make_opaque_sub("inference", annotation["inference"]))
    if "directional_vector" in annotation:
        main_annotation.subs.append(dt.make_opaque_sub("directional_vector", annotation["directional_vector"]))
    if "measures" in annotation:
        main_annotation.subs.append(dt.make_opaque_sub("measures", annotation["measures"]))
    if "auto_annotate" in annotation:
        main_annotation.subs.append(dt.make_opaque_sub("auto_annotate", annotation["auto_annotate"]))

    if "annotators" in annotation:
        main_annotation.annotators = _parse_annotators(annotation["annotators"])

    if "reviewers" in annotation:
        main_annotation.reviewers = _parse_annotators(annotation["reviewers"])

    return main_annotation


def _parse_darwin_video_annotation(annotation: dict) -> Optional[dt.VideoAnnotation]:
    name = annotation["name"]
    frame_annotations = {}
    keyframes: Dict[int, bool] = {}
    frames = {**annotation.get("frames", {}), **annotation.get("sections", {})}
    for f, frame in frames.items():
        frame_annotations[int(f)] = _parse_darwin_annotation({**frame, **{"name": name}})
        keyframes[int(f)] = frame.get("keyframe", False)

    if not frame_annotations:
        return None
    main_annotation = dt.make_video_annotation(
        frame_annotations,
        keyframes,
        annotation.get("ranges", annotation.get("segments", [])),
        annotation.get("interpolated", False),
        slot_names=parse_slot_names(annotation),
    )

    if "annotators" in annotation:
        main_annotation.annotators = _parse_annotators(annotation["annotators"])

    if "reviewers" in annotation:
        main_annotation.reviewers = _parse_annotators(annotation["reviewers"])

    return main_annotation


def _parse_annotators(annotators: List[Dict[str, Any]]) -> List[dt.AnnotationAuthor]:
    return [dt.AnnotationAuthor(annotator["full_name"], annotator["email"]) for annotator in annotators]


def split_video_annotation(annotation: dt.AnnotationFile) -> List[dt.AnnotationFile]:
    """
    Splits the given video ``AnnotationFile`` into several video ``AnnotationFile``s, one for each
    ``frame_url``.

    Parameters
    ----------
    annotation : dt.AnnotationFile
        The video ``AnnotationFile`` we want to split.

    Returns
    -------
    List[dt.AnnotationFile]
        A list with the split video ``AnnotationFile``\\s.

    Raises
    ------
    AttributeError
        If the given ``AnnotationFile`` is not a video annotation, or if the given annotation has
        no ``frame_url`` attribute.
    """
    if not annotation.is_video:
        raise AttributeError("this is not a video annotation")

    if not annotation.frame_urls:
        raise AttributeError("This Annotation has no frame urls")

    frame_annotations = []
    for i, frame_url in enumerate(annotation.frame_urls):
        annotations = [
            a.frames[i] for a in annotation.annotations if isinstance(a, dt.VideoAnnotation) and i in a.frames
        ]
        annotation_classes: Set[dt.AnnotationClass] = set([annotation.annotation_class for annotation in annotations])
        filename: str = f"{Path(annotation.filename).stem}/{i:07d}.png"
        frame_annotations.append(
            dt.AnnotationFile(
                annotation.path,
                filename,
                annotation_classes,
                annotations,
                False,
                annotation.image_width,
                annotation.image_height,
                frame_url,
                annotation.workview_url,
                annotation.seq,
                slots=annotation.slots,
            )
        )
    return frame_annotations


def parse_slot_names(annotation: dict) -> List[str]:
    return annotation.get("slot_names", [])


def ispolygon(annotation: dt.AnnotationClass) -> bool:
    """
    Returns whether or not the given ``AnnotationClass`` is a polygon.

    Parameters
    ----------
    annotation : AnnotationClass
        The ``AnnotationClass`` to evaluate.

    Returns
    -------
    ``True`` is the given ``AnnotationClass`` is a polygon, ``False`` otherwise.
    """
    return annotation.annotation_type in ["polygon", "complex_polygon"]


def convert_polygons_to_sequences(
    polygons: List[Union[dt.Polygon, List[dt.Polygon]]],
    height: Optional[int] = None,
    width: Optional[int] = None,
    rounding: bool = True,
) -> List[List[Union[int, float]]]:
    """
    Converts a list of polygons, encoded as a list of dictionaries of into a list of nd.arrays
    of coordinates.

    Parameters
    ----------
    polygons : Iterable[dt.Polygon]
        Non empty list of coordinates in the format ``[{x: x1, y:y1}, ..., {x: xn, y:yn}]`` or a
        list of them as ``[[{x: x1, y:y1}, ..., {x: xn, y:yn}], ..., [{x: x1, y:y1}, ..., {x: xn, y:yn}]]``.
    height : Optional[int], default: None
        Maximum height for a polygon coordinate.
    width : Optional[int], default: None
        Maximum width for a polygon coordinate.
    rounding : bool, default: True
        Whether or not to round values when creating sequences.

    Returns
    -------
    sequences: List[ndarray[float]]
        List of arrays of coordinates in the format [[x1, y1, x2, y2, ..., xn, yn], ...,
        [x1, y1, x2, y2, ..., xn, yn]]

    Raises
    ------
    ValueError
        If the given list is a falsy value (such as ``[]``) or if it's structure is incorrect.
    """
    if not polygons:
        raise ValueError("No polygons provided")
    # If there is a single polygon composing the instance then this is
    # transformed to polygons = [[{x: x1, y:y1}, ..., {x: xn, y:yn}]]
    list_polygons: List[dt.Polygon] = []
    if isinstance(polygons[0], list):
        list_polygons = cast(List[dt.Polygon], polygons)
    else:
        list_polygons = cast(List[dt.Polygon], [polygons])

    if not isinstance(list_polygons[0], list) or not isinstance(list_polygons[0][0], dict):
        raise ValueError("Unknown input format")

    sequences: List[List[Union[int, float]]] = []
    for polygon in list_polygons:
        path: List[Union[int, float]] = []
        for point in polygon:
            # Clip coordinates to the image size
            x = max(min(point["x"], width - 1) if width else point["x"], 0)
            y = max(min(point["y"], height - 1) if height else point["y"], 0)
            if rounding:
                path.append(round(x))
                path.append(round(y))
            else:
                path.append(x)
                path.append(y)
        sequences.append(path)
    return sequences


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="Do not use.",
)
def convert_sequences_to_polygons(
    sequences: List[Union[List[int], List[float]]], height: Optional[int] = None, width: Optional[int] = None
) -> Dict[str, List[dt.Polygon]]:
    """
    Converts a list of polygons, encoded as a list of dictionaries of into a list of nd.arrays
    of coordinates.

    Parameters
    ----------
    sequences : List[Union[List[int], List[float]]]
        List of arrays of coordinates in the format ``[x1, y1, x2, y2, ..., xn, yn]`` or as a list
        of them as ``[[x1, y1, x2, y2, ..., xn, yn], ..., [x1, y1, x2, y2, ..., xn, yn]]``.
    height : Optional[int], default: None
        Maximum height for a polygon coordinate.
    width : Optional[int], default: None
        Maximum width for a polygon coordinate.

    Returns
    -------
    Dict[str, List[dt.Polygon]]
        Dictionary with the key ``path`` containing a list of coordinates in the format of
        ``[[{x: x1, y:y1}, ..., {x: xn, y:yn}], ..., [{x: x1, y:y1}, ..., {x: xn, y:yn}]]``.

    Raises
    ------
    ValueError
        If sequences is a falsy value (such as ``[]``) or if it is in an incorrect format.
    """
    if not sequences:
        raise ValueError("No sequences provided")
    # If there is a single sequences composing the instance then this is
    # transformed to polygons = [[x1, y1, ..., xn, yn]]
    if not isinstance(sequences[0], list):
        sequences = [sequences]

    if not isinstance(sequences[0][0], (int, float)):
        raise ValueError("Unknown input format")

    def grouped(iterable, n):
        return zip(*[iter(iterable)] * n)

    polygons = []
    for sequence in sequences:
        path = []
        for x, y in grouped(sequence, 2):
            # Clip coordinates to the image size
            x = max(min(x, width - 1) if width else x, 0)
            y = max(min(y, height - 1) if height else y, 0)
            path.append({"x": x, "y": y})
        polygons.append(path)
    return {"path": polygons}


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="Do not use.",
)
def convert_xyxy_to_bounding_box(box: List[Union[int, float]]) -> dt.BoundingBox:
    """
    Converts a list of xy coordinates representing a bounding box into a dictionary.

    Parameters
    ----------
    box : List[Union[int, float]]
        List of arrays of coordinates in the format [x1, y1, x2, y2]

    Returns
    -------
    BoundingBox
        Bounding box in the format ``{x: x1, y: y1, h: height, w: width}``.

    Raises
    ------
    ValueError
        If ``box`` has an incorrect format.
    """
    if not isinstance(box[0], float) and not isinstance(box[0], int):
        raise ValueError("Unknown input format")

    x1, y1, x2, y2 = box
    width = x2 - x1
    height = y2 - y1
    return {"x": x1, "y": y1, "w": width, "h": height}


@deprecation.deprecated(
    deprecated_in="0.7.5",
    removed_in="0.8.0",
    current_version=__version__,
    details="Do not use.",
)
def convert_bounding_box_to_xyxy(box: dt.BoundingBox) -> List[float]:
    """
    Converts dictionary representing a bounding box into a list of xy coordinates.

    Parameters
    ----------
    box : BoundingBox
        Bounding box in the format ``{x: x1, y: y1, h: height, w: width}``.

    Returns
    -------
    List[float]
        List of arrays of coordinates in the format ``[x1, y1, x2, y2]``.
    """

    x2 = box["x"] + box["width"]
    y2 = box["y"] + box["height"]
    return [box["x"], box["y"], x2, y2]


def convert_polygons_to_mask(polygons: List, height: int, width: int, value: Optional[int] = 1) -> np.ndarray:
    """
    Converts a list of polygons, encoded as a list of dictionaries into an ``nd.array`` mask.

    Parameters
    ----------
    polygons: list
        List of coordinates in the format ``[{x: x1, y:y1}, ..., {x: xn, y:yn}]`` or a list of them
        as  ``[[{x: x1, y:y1}, ..., {x: xn, y:yn}], ..., [{x: x1, y:y1}, ..., {x: xn, y:yn}]]``.
    height : int
        The maximum height for the created mask.
    width : int
        The maximum width for the created mask.
    value : Optional[int], default: 1
        The drawing value for ``upolygon``.

    Returns
    -------
    ndarray
        ``ndarray`` mask of the polygon(s).
    """
    sequence = convert_polygons_to_sequences(polygons, height=height, width=width)
    mask = np.zeros((height, width)).astype(np.uint8)
    draw_polygon(mask, sequence, value)
    return mask


def chunk(items: List[Any], size: int) -> Iterator[Any]:
    """
    Splits the given list into chunks of the given size and yields them.

    Parameters
    ----------
    items : List[Any]
        The list of items to be split.
    size : int
        The size of each split.

    Yields
    ------
    Iterator[Any]
        A chunk of the of the given size.
    """
    for i in range(0, len(items), size):
        yield items[i : i + size]


def is_unix_like_os() -> bool:
    """
    Returns ``True`` if the executing OS is Unix-based (Ubuntu or MacOS, for example) or ``False``
    otherwise.

    Returns
    --------
    bool
        True for Unix-based systems, False otherwise.
    """
    return platform.system() != "Windows"


def has_json_content_type(response: Response) -> bool:
    """
    Returns ``True`` if response has application/json content type or ``False``
    otherwise.

    Returns
    --------
    bool
        True for application/json content type, False otherwise.
    """
    return "application/json" in response.headers.get("content-type", "")


def get_response_content(response: Response) -> Any:
    """
    Returns json content if response has application/json content-type, otherwise returns text.

    Returns
    --------
    Any
        Json or text content.
    """
    if has_json_content_type(response):
        return response.json()
    else:
        return response.text


def _parse_version(data) -> dt.AnnotationFileVersion:
    version_string = data.get("version", "1.0")
    major, minor, suffix = re.findall(r"^(\d+)\.(\d+)(.*)$", version_string)[0]
    return dt.AnnotationFileVersion(int(major), int(minor), suffix)


def _data_to_annotations(data: Dict[str, Any]) -> List[Union[dt.Annotation, dt.VideoAnnotation]]:
    raw_image_annotations = filter(lambda annotation: "frames" not in annotation, data["annotations"])
    raw_video_annotations = filter(lambda annotation: "frames" in annotation, data["annotations"])
    image_annotations: List[dt.Annotation] = list(filter(None, map(_parse_darwin_annotation, raw_image_annotations)))
    video_annotations: List[dt.VideoAnnotation] = list(
        filter(None, map(_parse_darwin_video_annotation, raw_video_annotations))
    )
    return [*image_annotations, *video_annotations]


def _supported_schema_versions():
    return {(2, 0, ""): "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json"}


def _default_schema(version: dt.AnnotationFileVersion):
    return _supported_schema_versions().get((version.major, version.minor, version.suffix))
