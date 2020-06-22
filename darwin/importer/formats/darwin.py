import json
from pathlib import Path
from typing import Optional

import darwin.datatypes as dt
from darwin.utils import parse_darwin_annotation


def parse_file(path: Path) -> Optional[dt.AnnotationFile]:
    if path.suffix != ".json":
        return
    with path.open() as f:
        data = json.load(f)
        annotations = list(filter(None, map(parse_darwin_annotation, data["annotations"])))
        annotation_classes = set([annotation.annotation_class for annotation in annotations])
        filename = data["image"]["original_filename"]
        return dt.AnnotationFile(path, filename, annotation_classes, annotations)
