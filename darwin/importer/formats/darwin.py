import json
import os
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
        image = data["image"]
        # filename = f"{image['original_filename']}"
        filename = f"{os.splitext(image['filename'])[0]_image['original_filename']}"
        return dt.AnnotationFile(path, filename, annotation_classes, annotations)


def _parse_annotation(annotation):
    annotation_label = annotation["name"]

    if "polygon" in annotation:
        return dt.make_polygon(annotation_label, annotation["polygon"]["path"])
    if "complex_polygon" in annotation:
        return dt.make_complex_polygon(annotation_label, annotation["complex_polygon"]["path"])
    if "bounding_box" in annotation:
        bbox = annotation["bounding_box"]
        return dt.make_bounding_box(annotation_label, bbox["x"], bbox["y"], bbox["w"], bbox["h"])
    if "tag" in annotation:
        return dt.make_tag(annotation_label)
    # TODO: import instance_id, text, attribute
    return

