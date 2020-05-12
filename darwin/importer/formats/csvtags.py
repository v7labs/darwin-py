from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt


def parse_file(path: Path) -> Optional[List[dt.AnnotationFile]]:
    if path.suffix != ".csv":
        return

    files = []
    with path.open() as f:
        for line in f:
            filename, *tags = map(lambda s: s.strip(), line.split(","))
            annotations = [dt.make_tag(tag) for tag in tags]
            annotation_classes = set([annotation.annotation_class for annotation in annotations])
            files.append(dt.AnnotationFile(path, filename, annotation_classes, annotations))
    return files
