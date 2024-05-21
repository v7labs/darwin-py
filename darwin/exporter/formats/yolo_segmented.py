from collections import namedtuple
from enum import Enum, auto
from logging import getLogger
from pathlib import Path
from typing import Iterable, List

from darwin.datatypes import Annotation, AnnotationFile, VideoAnnotation
from darwin.exceptions import DarwinException
from darwin.exporter.formats.helpers.yolo_class_builder import (
    ClassIndex,
    build_class_index,
    export_file,
    save_class_index,
)

logger = getLogger(__name__)

CLOSE_VERTICES: bool = False  # Set true if polygons need to be closed


Point = namedtuple("Point", ["x", "y"])


def export(annotation_files: Iterable[AnnotationFile], output_dir: Path) -> None:
    """
    Exports YoloV8 format as segments

    Parameters
    ----------
    annotation_files : Iterable[AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new pascalvoc files will be.

    Returns
    -------
    None
    """
    annotation_files = list(annotation_files)

    class_index: ClassIndex = build_class_index(
        # fmt: off
        annotation_files, ["bounding_box", "polygon"]
    )  # fmt: on

    for annotation_file in annotation_files:
        export_file(annotation_file, class_index, output_dir, _build_text)

    save_class_index(class_index, output_dir)


def normalise(value: float, height_or_width: int) -> float:
    """
    Normalises the value to a proportion of the image size

    Parameters
    ----------
    value : float
        The value to be normalised.
    height_or_width : Union[float, int]
        The height or width of the image.

    Returns
    -------
    float
        The normalised value.
    """
    return value / height_or_width


class YoloSegmentedAnnotationType(Enum):
    """
    The YoloV8 annotation types
    """

    UNKNOWN = auto()
    BOUNDING_BOX = auto()
    POLYGON = auto()


def _determine_annotation_type(annotation: Annotation) -> YoloSegmentedAnnotationType:
    """
    Determines the annotation type

    Parameters
    ----------
    annotation : Annotation
        The annotation to be determined.

    Returns
    -------
    YoloSegmentedAnnotationType
        The annotation type.
    """
    type = annotation.annotation_class.annotation_type

    if type == "bounding_box":
        return YoloSegmentedAnnotationType.BOUNDING_BOX
    elif type == "polygon":
        return YoloSegmentedAnnotationType.POLYGON
    else:
        return YoloSegmentedAnnotationType.UNKNOWN


def _handle_bounding_box(
    data: dict, im_w: int, im_h: int, annotation_index: int, points: List[Point]
) -> bool:
    logger.debug(f"Exporting bounding box at index {annotation_index}.")

    try:
        # Create 8 coordinates for the x,y pairs of the 4 corners
        x1, y1, x2, y2, x3, y3, x4, y4, x5, y5 = (
            # top left corner
            data["x"],
            data["y"],
            # top right corner
            (data["x"] + data["w"]),
            (data["y"]),
            # bottom right
            (data["x"] + data["w"]),
            (data["y"] + data["h"]),
            # bottom left
            data["x"],
            (data["y"] + data["h"]),
            # top left again to close the polygon
            data["x"],
            data["y"],
        )

        logger.debug(
            "Coordinates for bounding box: "
            f"({x1}, {y1}), ({x2}, {y2}), "
            f"({x3}, {y3}), ({x4}, {y4}), "
            f"({x5}, {y5})"  # Unsure if we have to close this.
        )

        # Normalize the coordinates to a proportion of the image size
        n_x1 = normalise(x1, im_w)
        n_y1 = normalise(y1, im_h)
        n_x2 = normalise(x2, im_w)
        n_y2 = normalise(y2, im_h)
        n_x3 = normalise(x3, im_w)
        n_y3 = normalise(y3, im_h)
        n_x4 = normalise(x4, im_w)
        n_y4 = normalise(y4, im_h)
        n_x5 = normalise(x5, im_w)
        n_y5 = normalise(y5, im_w)

        logger.debug(
            "Normalized coordinates for bounding box: "
            f"({n_x1}, {n_y1}), ({n_x2}, {n_y2}), "
            f"({n_x3}, {n_y3}), ({n_x4}, {n_y4}), "
            f"({n_x5}, {n_y5})"
        )

        # Add the coordinates to the points list
        points.append(Point(x=n_x1, y=n_y1))
        points.append(Point(x=n_x2, y=n_y2))
        points.append(Point(x=n_x3, y=n_y3))
        points.append(Point(x=n_x4, y=n_y4))

        if CLOSE_VERTICES:
            points.append(Point(x=n_x5, y=n_y5))

    except KeyError as exc:
        logger.warn(
            f"Skipped annotation at index {annotation_index} because an"
            "expected key was not found in the data.",
            exc_info=exc,
        )
        return False

    return True


def _handle_polygon(
    data: dict, im_w: int, im_h: int, annotation_index: int, points: List[Point]
) -> bool:
    logger.debug(f"Exporting polygon at index {annotation_index}.")

    last_point = None
    try:
        if "paths" in data:
            paths_data = data["paths"]
            if len(paths_data) > 1:
                raise DarwinException from ValueError(
                    "Complex polygon detected. The YOLOV8 format only supports simple polygons with a single path."
                )
            path_data = paths_data[0]
        # Continuing to support old versions, in case anything relies on it.
        elif "path" in data:
            path_data = data["path"]
        elif "points" in data:
            path_data = data["points"]
        else:
            raise DarwinException from ValueError("No path data found in annotation.")

        for point_index, point in enumerate(path_data):
            last_point = point_index
            x = point["x"] / im_w
            y = point["y"] / im_h
            points.append(Point(x=x, y=y))

        if CLOSE_VERTICES:
            points.append(points[0])

    except KeyError as exc:
        logger.warn(
            (
                f"Skipped annotation at index {annotation_index} because an"
                "expected key was not found in the data."
                f"Error occured while calculating point at index {last_point}."
                if last_point
                else "Error occured while enumerating points."
            ),
            exc_info=exc,
        )
        return False

    except Exception:
        logger.error(
            f"An unexpected error occured while exporting annotation at index {annotation_index}."
        )

    return True


def _build_text(annotation_file: AnnotationFile, class_index: ClassIndex) -> str:
    """
    Builds the YoloV8 format as segments

    Parameters
    ----------
    annotation_file : AnnotationFile
        The ``AnnotationFile`` to be exported.
    class_index : ClassIndex
        The class index.

    Returns
    -------
    str
        The YoloV8 format as segments
    """
    yolo_lines: List[str] = []

    im_w = annotation_file.image_width
    im_h = annotation_file.image_height

    if not im_w or not im_h:
        raise ValueError(
            "Annotation file has no image width or height. "
            "YoloV8 Segments are encoded as a proportion of height and width. "
            "This file cannot be YoloV8 encoded without image dimensions."
        )

    for annotation_index, annotation in enumerate(annotation_file.annotations):
        # Sanity checks
        if isinstance(annotation, VideoAnnotation):
            logger.warn(
                f"Skipped annotation at index {annotation_index} because video annotations don't contain the needed data."
            )
            continue

        if annotation.data is None:
            logger.warn(
                f"Skipped annotation at index {annotation_index} because it's data fields are empty.'"
            )
            continue

        # Process annotations

        annotation_type = _determine_annotation_type(annotation)
        if annotation_type == YoloSegmentedAnnotationType.UNKNOWN:
            continue

        data = annotation.data
        points: List[Point] = []

        if annotation_type == YoloSegmentedAnnotationType.BOUNDING_BOX:
            bb_success = _handle_bounding_box(
                data, im_w, im_h, annotation_index, points
            )
            if not bb_success:
                continue
        elif annotation_type == YoloSegmentedAnnotationType.POLYGON:
            polygon_success = _handle_polygon(
                data, im_w, im_h, annotation_index, points
            )
            if not polygon_success:
                continue
        else:
            logger.warn(
                f"Skipped annotation at index {annotation_index} because it's annotation type is not supported."
            )
            continue

        if len(points) < 3:
            logger.warn(
                f"Skipped annotation at index {annotation_index} because it "
                "has less than 3 points.  Any valid polygon must have at least"
                " 3 points."
            )
            continue

        # Create the line for the annotation
        yolo_line = f"{class_index[annotation.annotation_class.name]} {' '.join([f'{p.x} {p.y}' for p in points])}"
        yolo_lines.append(yolo_line)
    return "\n".join(yolo_lines) + "\n"
