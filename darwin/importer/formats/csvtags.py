import csv
from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt


def parse_file(path: Path) -> Optional[List[dt.AnnotationFile]]:
    if path.suffix != ".csv":
        return

    files = []
    with path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            filename, *tags = map(lambda s: s.strip(), row)
            if filename == "":
                continue
            annotations = [dt.make_tag(tag) for tag in tags if len(tag) > 0]
            annotation_classes = set([annotation.annotation_class for annotation in annotations])
            files.append(dt.AnnotationFile(path, filename, annotation_classes, annotations))
    return files
