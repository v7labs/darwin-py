from collections import namedtuple
from pathlib import Path
from typing import Iterable, List

from darwin.datatypes import AnnotationFile, VideoAnnotation
from darwin.exporter.formats.helpers.yolo_class_builder import (
    ClassIndex,
    build_class_index,
    export_file,
    save_class_index,
)


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

    class_index: ClassIndex = build_class_index(annotation_files, ["bounding_box", "polygon"])

    for annotation_file in annotation_files:
        export_file(annotation_file, class_index, output_dir, _build_text)

    save_class_index(class_index, output_dir)


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

    for annotation in annotation_file.annotations:
        annotation_type = annotation.annotation_class.annotation_type

        if isinstance(annotation, VideoAnnotation):
            raise ValueError("YOLO format does not support video annotations for export or conversion.")

        Point = namedtuple("Point", ["x", "y"])

        if annotation.data is None:
            continue

        data = annotation.data
        points: List[Point] = []

        if annotation_type == "bounding_box":
            points.append(Point(x=data["x"], y=data["y"]))
            points.append(Point(x=data["x"] + data["w"], y=data["y"]))
            points.append(Point(x=data["x"] + data["w"], y=data["y"] + data["h"]))
            points.append(Point(x=data["x"], y=data["y"] + data["h"]))
        elif annotation_type == "polygon":
            for point in data["points"]:
                points.append(Point(x=point["x"], y=point["y"]))
        else:
            continue

        #! As yet untested
        for i in range(0, len(points), 2):
            x1, y1 = points[i].x, points[i].y
            x2, y2 = points[i + 1].x, points[i + 1].y

            yolo_lines.append(f"{class_index[annotation.annotation_class.name]} {x1} {y1} {x2} {y2}")
