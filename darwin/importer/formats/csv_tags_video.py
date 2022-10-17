import csv
from pathlib import Path
from typing import Dict, List, Optional, Union

import darwin.datatypes as dt


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses the given ``csv video`` file and returns a ``List[dt.AnnotationFile]``, or ``None`` if
    the extension of the given file is not ``.csv``.

    Parameters
    ----------
    path : Path
        The ``Path`` to the file to be parsed.

    Returns
    -------
    Optional[List[dt.AnnotationFile]]
        A ``List[dt.AnnotationFile]`` or ``None`` if the file was parseable.
    """
    if path.suffix != ".csv":
        return None

    files = []

    file_annotation_map: Dict[str, List[Union[dt.Annotation, dt.VideoAnnotation]]] = {}
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

            annotation = dt.make_video_annotation(frames, keyframes, [[start_frame, end_frame]], False, slot_names=[])
            if filename not in file_annotation_map:
                file_annotation_map[filename] = []
            file_annotation_map[filename].append(annotation)
    for filename in file_annotation_map:
        annotations = file_annotation_map[filename]
        annotation_classes = set([annotation.annotation_class for annotation in annotations])
        files.append(dt.AnnotationFile(path, filename, annotation_classes, annotations, is_video=True, remote_path="/"))
    return files
