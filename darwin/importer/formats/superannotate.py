import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import darwin.datatypes as dt


def parse_file(path: Path, classes_path: Optional[Path] = None) -> Optional[List[dt.AnnotationFile]]:
    if path.suffix != ".json":
        return None

    with path.open() as f:
        parsed_annotations = json.load(f)

    fallback_classes_path: Path = classes_path or (path.parent / "classes.json")
    with fallback_classes_path.open() as f:
        parsed_classes = json.load(f)

    annotation_files: List[dt.AnnotationFile] = []

    for filename, data in parsed_annotations.items():
        # Skip internal metadata
        if filename == "___sa_version___":
            continue

        # Raise error if an item does not contain any annotations
        if "instances" not in data:
            raise ValueError(f"No instances found in {path}")

        annotations: List[dt.Annotation] = [
            _parse_annotation(annotation, parsed_classes) for annotation in data["instances"]
        ]
        classes = set([annotation.annotation_class for annotation in annotations])

        annotation_files.append(dt.AnnotationFile(path, filename, classes, annotations, remote_path="/"))

    return annotation_files


def _parse_annotation(annotation, classes) -> dt.Annotation:
    annotation_type = annotation["type"]

    class_id = annotation["classId"]
    annotation_label = _find_class(classes, class_id)
    if annotation_label is None:
        raise ValueError(f"Class ID {class_id} not found")

    if annotation_type == "bbox":
        points = annotation["points"]
        x1 = points["x1"]
        y1 = points["y1"]
        x2 = points["x2"]
        y2 = points["y2"]
        return dt.make_bounding_box(annotation_label, x1, y1, x2 - x1, y2 - y1)

    if annotation_type == "point":
        x = annotation["x"]
        y = annotation["y"]
        return dt.make_keypoint(annotation_label, x, y)

    if annotation_type == "polygon":
        point_list = annotation["points"]
        points = [{"x": point_list[i], "y": point_list[i + 1]} for i in range(0, len(point_list), 2)]
        return dt.make_polygon(annotation_label, points)

    if annotation_type == "polyline":
        point_list = annotation["points"]
        points = [{"x": point_list[i], "y": point_list[i + 1]} for i in range(0, len(point_list), 2)]
        return dt.make_line(annotation_label, points)

    # TODO: Add support for "cuboid" and "ellipse" annotation types
    raise ValueError(f"Unknown supported annotation type: {annotation_type}")


def _find_class(classes: List[Dict[str, Any]], class_id: int) -> Optional[str]:
    for c in classes:
        if c["id"] == class_id:
            return c["name"]
    return None
