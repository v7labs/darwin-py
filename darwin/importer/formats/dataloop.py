import json
from pathlib import Path
from typing import Optional

import darwin.datatypes as dt


def parse_file(path: Path) -> Optional[dt.AnnotationFile]:
    if path.suffix != ".json":
        return
    with path.open() as f:
        data = json.load(f)
        annotations = list(filter(None, map(_parse_annotation, data["annotations"])))
        annotation_classes = set([annotation.annotation_class for annotation in annotations])
        return dt.AnnotationFile(path, _remove_leading_slash(data["filename"]), annotation_classes, annotations)


def _remove_leading_slash(filename):
    if filename[0] == "/":
        return filename[1:]
    else:
        return filename


def _parse_annotation(annotation):
    annotation_type = annotation["type"]
    annotation_label = annotation["label"]
    if annotation_type not in ["box", "class"]:
        raise ValueError(f"Unknown supported annotation type: {annotation_type}")

    if len(annotation["metadata"]["system"]["snapshots_"]) > 1:
        raise ValueError("multiple snapshots per annotations are not supported")

    # Class is metadata that we can ignore
    if annotation_type == "class":
        return
    if annotation_type == "box":
        coords = annotation["coordinates"]
        x1, y1 = coords[0]["x"], coords[0]["y"]
        x2, y2 = coords[1]["x"], coords[1]["y"]
        return dt.make_bounding_box(annotation_label, x1, y1, x2 - x1, y2 - y1)
