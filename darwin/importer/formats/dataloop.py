from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import orjson as json

import darwin.datatypes as dt
from darwin.exceptions import (
    DataloopComplexPolygonsNotYetSupported,
    UnsupportedImportAnnotationType,
)


def parse_path(path: Path) -> Optional[dt.AnnotationFile]:
    """
    Parses the given ``dataloop`` file and returns the corresponding darwin ``AnnotationFile``, or
    ``None`` if the file's extension is not ``.json``.

    Parameters
    ----------
    path : Path
        The ``Path`` of the file to parse.

    Returns
    -------
    Optional[dt.AnnotationFile]
        The corresponding ``AnnotationFile``, or ``None`` if the given file was not parseable.

    """
    if path.suffix != ".json":
        return None
    with path.open() as f:
        data = json.loads(f.read())
        annotations: List[dt.Annotation] = list(filter(None, map(_parse_annotation, data["annotations"])))
        annotation_classes: Set[dt.AnnotationClass] = set([annotation.annotation_class for annotation in annotations])
        return dt.AnnotationFile(
            path,
            _remove_leading_slash(data["filename"]),
            annotation_classes,
            annotations,
            remote_path="/",
        )


def _remove_leading_slash(filename: str) -> str:
    if filename[0] == "/":
        return filename[1:]
    else:
        return filename


def _parse_annotation(annotation: Dict[str, Any]) -> Optional[dt.Annotation]:
    annotation_type = annotation["type"]
    annotation_label = annotation["label"]
    if annotation_type not in ["box", "class", "segment"]:
        raise UnsupportedImportAnnotationType("dataloop", annotation_type)

    if len(annotation["metadata"]["system"].get("snapshots_", [])) > 1:
        raise ValueError("multiple snapshots per annotations are not supported")

    # Class is metadata that we can ignore
    if annotation_type == "class":
        return None

    if annotation_type == "box":
        coords = annotation["coordinates"]
        x1, y1 = coords[0]["x"], coords[0]["y"]
        x2, y2 = coords[1]["x"], coords[1]["y"]
        return dt.make_bounding_box(annotation_label, x1, y1, x2 - x1, y2 - y1)

    if annotation_type == "segment":
        coords = annotation["coordinates"]
        if len(coords) != 1:
            raise DataloopComplexPolygonsNotYetSupported()

        points: List[dt.Point] = [{"x": c["x"], "y": c["y"]} for c in coords[0]]
        return dt.make_polygon(annotation_label, point_path=points)

    return None
