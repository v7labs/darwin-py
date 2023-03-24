from functools import reduce
from pathlib import Path
from typing import Dict, Iterable

import darwin.datatypes as dt

ClassIndex = Dict[str, int]


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

    class_index = _build_class_index(annotation_files)

    for annotation_file in annotation_files:
        _export_file(annotation_file, class_index, output_dir)

    _save_class_index(class_index, output_dir)


def _export_file(annotation_file: dt.AnnotationFile, class_index: ClassIndex, output_dir: Path) -> None:
    txt = _build_txt(annotation_file, class_index)
    output_file_path = (output_dir / "train" / "labels" / annotation_file.filename).with_suffix(".txt")
    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "w") as f:
        f.write(txt)


def _build_class_index(annotation_files: Iterable[dt.AnnotationFile]) -> ClassIndex:
    classes = set()
    for annotation_file in annotation_files:
        for annotation in annotation_file.annotations:
            if annotation.annotation_class.annotation_type in ["bounding_box", "polygon", "complex_polygon"]:
                classes.add(annotation.annotation_class.name)
    return {k: v for (v, k) in enumerate(sorted(classes))}


def _build_txt(annotation_file: dt.AnnotationFile, class_index: ClassIndex) -> str:
    yolo_lines = []
    if annotation_file.image_height is None or annotation_file.image_width is None:
        return ""
    imh = annotation_file.image_height
    imw = annotation_file.image_width
    for annotation in annotation_file.annotations:
        if annotation.data is None:
            continue
        annotation_type = annotation.annotation_class.annotation_type
        i = class_index[annotation.annotation_class.name]
        if annotation_type == "bounding_box":
            data = annotation.data
            # x, y should be the center of the box
            # x, y, w, h are normalized to the image size
            x = data["x"] + data["w"] / 2
            y = data["y"] + data["h"] / 2
            w = data["w"]
            h = data["h"]
            x = x / imw
            y = y / imh
            w = w / imw
            h = h / imh

            yolo_lines.append(f"{i} {x} {y} {w} {h}")
        elif annotation_type in ["polygon", "complex_polygon"]:
            data = annotation.data
            # Polygons are a list of point
            coords = " ".join([f"{item.get('x')/imw} {item.get('y')/imh}" for item in data.get('path')])
            i = class_index[annotation.annotation_class.name]
            yolo_lines.append(f"{i} {coords}")
        else:
            print(f"Not a known annotation type {annotation_type}")

    return "\n".join(yolo_lines)


def _save_class_index(class_index: ClassIndex, output_dir: Path) -> None:
    sorted_items = sorted(class_index.items(), key=lambda item: item[1])

    with open(output_dir / "dataset.yaml", "w") as f:
        f.write("train: ../train/images\n")
        f.write("valid: ../valid/images\n")
        f.write("test: ../test/images\n\n")
        f.write(f"nc: {len(sorted_items)}\n")
        labels = ", ".join([f"'{item[0]}'" for item in sorted_items])
        f.write(f"names: [{labels}]\n")
