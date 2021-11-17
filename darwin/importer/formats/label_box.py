import json
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    make_bounding_box,
)


def parse_file(path: Path) -> Optional[List[AnnotationFile]]:
    """
    Parses the given LabelBox file and maybe returns the corresponding annotations.
    The file must have the following structure:
    
    ```json
    [
        {
            "Label":{
                "objects":[
                    {
                        "bbox":{"top":3558, "left":145, "height":623, "width":449}
                    },
                    {...}
                ]
            },
            "External ID": "demo-image-7.jpg"
        },
        {...}
    ]
    ```

    Currently we support the following annotations:
    - bounding-box `Image`: https://docs.labelbox.com/docs/bounding-box-json

    Parameters
    --------
    path: Path
        The path of the file to parse.

    Returns
    -------
    Optional[List[darwin.datatypes.AnnotationFile]]
        The AnnotationFiles with the parsed information from the file or None, if the file is not a 
        `json` file.

    Raises
    ------
    ValueError
        If the given JSON file is malformed or if it has an unknown annotation. 
        To see a list of possible annotation formats go to:
        https://docs.labelbox.com/docs/annotation-types-1

    """
    if path.suffix != ".json":
        return None

    with path.open() as f:
        data = json.load(f)
        convert_with_path = partial(_convert, path=path)

        return list(map(convert_with_path, data))


def _convert(file_data: Dict[str, Any], path) -> AnnotationFile:
    filename: Optional[str] = file_data.get("External ID")
    if not filename:
        raise ValueError(f"LabelBox Object must have an 'External ID' key: {file_data}")

    label: Optional[Dict[str, Any]] = file_data.get("Label")
    if label is None:
        raise ValueError(f"LabelBox Object must have a 'Label' key: {file_data}")

    label_objects: Optional[List[Dict[str, Any]]] = label.get("objects")
    if label_objects is None:
        raise ValueError(f"LabelBox Label must have an 'objects' key: {file_data}")

    annotations: List[Annotation] = list(map(_convert_label_objects, label_objects))
    classes: Set[AnnotationClass] = set(map(_get_class, annotations))
    return AnnotationFile(
        annotations=annotations, path=path, filename=filename, annotation_classes=classes, remote_path="/"
    )


def _convert_label_objects(obj: Dict[str, Any]) -> Annotation:
    title: Optional[str] = obj.get("title")
    if not title:
        raise ValueError(f"LabelBox objects must have a title: {obj}")

    bbox: Optional[Dict[str, Any]] = obj.get("bbox")
    if bbox:
        return _to_bbox_annotation(bbox, title)

    raise ValueError(f"Unsupported object type {obj}")


def _to_bbox_annotation(bbox: Dict[str, Any], title: str) -> Annotation:
    x: Optional[float] = bbox.get("left")
    if x is None:
        raise ValueError(f"bbox objects must have a 'left' value: {bbox}")

    y: Optional[float] = bbox.get("top")
    if y is None:
        raise ValueError(f"bbox objects must have a 'top' value: {bbox}")

    width: Optional[float] = bbox.get("width")
    if width is None:
        raise ValueError(f"bbox objects must have a 'width' value: {bbox}")

    height: Optional[float] = bbox.get("height")
    if height is None:
        raise ValueError(f"bbox objects must have a 'height' value: {bbox}")

    return make_bounding_box(title, x, y, width, height)


def _get_class(annotation: Annotation) -> AnnotationClass:
    return annotation.annotation_class

