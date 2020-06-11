import json
import os
from pathlib import Path
from typing import Optional

import darwin.datatypes as dt
from darwin.utils import _parse_darwin_annotation


def parse_file(path: Path) -> Optional[dt.AnnotationFile]:
    if path.suffix != ".json":
        return
    with path.open() as f:
        data = json.load(f)
        annotations = list(filter(None, map(_parse_darwin_annotation, data["annotations"])))
        annotation_classes = set([annotation.annotation_class for annotation in annotations])
        # filename = f"{data['image']['original_filename']}"
        filename = path.stem + os.path.splitext(data["image"]["original_filename"])[1]
        return dt.AnnotationFile(path, filename, annotation_classes, annotations)
