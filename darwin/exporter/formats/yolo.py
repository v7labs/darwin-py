from pathlib import Path
from typing import Iterable

import darwin.datatypes as dt
from darwin.exporter.formats.helpers.yolo_class_builder import (
    ClassIndex,
    build_class_index,
    export_file,
    save_class_index,
)


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into the YOLO format inside of the given
    ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new pascalvoc files will be.
    """

    annotation_files = list(annotation_files)

    class_index = build_class_index(annotation_files)

    for annotation_file in annotation_files:
        export_file(annotation_file, class_index, output_dir, _build_txt)

    save_class_index(class_index, output_dir)


def _build_txt(annotation_file: dt.AnnotationFile, class_index: ClassIndex) -> str:
    yolo_lines = []
    for annotation in annotation_file.annotations:
        annotation_type = annotation.annotation_class.annotation_type

        if isinstance(annotation, dt.VideoAnnotation):
            raise ValueError(
                "YOLO format does not support video annotations for export or conversion."
            )

        if annotation_type == "bounding_box":
            data = annotation.data
        elif annotation_type == "polygon":
            data = annotation.data
            data = data.get("bounding_box")
        else:
            continue

        if annotation.data is None:
            continue
        if annotation_file.image_height is None or annotation_file.image_width is None:
            continue

        i = class_index[annotation.annotation_class.name]
        # x, y should be the center of the box
        # x, y, w, h are normalized to the image size
        x = data["x"] + data["w"] / 2
        y = data["y"] + data["h"] / 2
        w = data["w"]
        h = data["h"]
        imh = annotation_file.image_height
        imw = annotation_file.image_width
        x = x / imw
        y = y / imh
        w = w / imw
        h = h / imh

        yolo_lines.append(f"{i} {x} {y} {w} {h}")
    return "\n".join(yolo_lines)
