import csv
from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt


def parse_file(path: Path) -> Optional[List[dt.AnnotationFile]]:
    if path.suffix != ".csv":
        return

    files = []

    file_annotation_map = {}
    with path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            try:
                filename, tag, start_frame, end_frame = map(lambda s: s.strip(), row)
            except ValueError:
                continue
            if filename == "":
                continue

            start_frame = int(start_frame)
            end_frame = int(end_frame)

            annotation = dt.make_tag(tag)
            frames = {i: annotation for i in range(start_frame, end_frame + 1)}
            keyframes = {i: i == start_frame for i in range(start_frame, end_frame + 1)}

            annotation = dt.make_video_annotation(frames, keyframes, [[start_frame, end_frame]], False)
            if filename not in file_annotation_map:
                file_annotation_map[filename] = []
            file_annotation_map[filename].append(annotation)
    for filename in file_annotation_map:
        annotations = file_annotation_map[filename]
        annotation_classes = set([annotation.annotation_class for annotation in annotations])
        files.append(dt.AnnotationFile(path, filename, annotation_classes, annotations, is_video=True))
    return files
