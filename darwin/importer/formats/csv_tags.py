import csv
from pathlib import Path
from typing import List, Optional

import darwin.datatypes as dt
from darwin.path_utils import deconstruct_full_path


def parse_path(path: Path) -> Optional[List[dt.AnnotationFile]]:
    """
    Parses the given file and returns a ``List[dt.AnnotationFile]`` with the parsed files, or
    ``None`` if the given file's extension is not ``.csv``.

    Parameters
    ----------
    path : Path
        The ``Path`` of the file to parse.

    Returns
    -------
    Optional[List[dt.AnnotationFile]]
        A ``List[dt.AnnotationFile]`` or ``None`` if the function was not able to parse the file.
    """
    if path.suffix != ".csv":
        return None

    files = []
    tags_and_files = {}
    with path.open() as f:
        reader = csv.reader(f)
        for row in reader:
            filename, *tags = (s.strip() for s in row)
            if filename == "":
                continue
            annotations = [dt.make_tag(tag) for tag in tags if len(tag) > 0]
            if filename not in tags_and_files:
                tags_and_files[filename] = list(annotations)
            else:
                tags_and_files[filename].extend(annotations)

        for filename, annotations in tags_and_files.items():
            annotation_classes = {
                annotation.annotation_class for annotation in annotations
            }
            remote_path, filename = deconstruct_full_path(filename)
            files.append(
                dt.AnnotationFile(
                    path,
                    filename,
                    annotation_classes,
                    annotations,
                    remote_path=remote_path,
                )
            )
    return files
