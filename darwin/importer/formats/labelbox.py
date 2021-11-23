import json
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, cast

from jsonschema_rs import JSONSchema

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    Point,
    make_bounding_box,
    make_polygon,
)


def parse_file(path: Path, validator: JSONSchema) -> Optional[List[AnnotationFile]]:
    """
    Parses the given LabelBox file and maybe returns the corresponding annotations.
    The file must have a structure simillar to the following:
    
    ```json
    [
        {
            "Label":{
                "objects":[
                    {
                        "title": "SomeTitle",
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
    - polygon `Image`: https://docs.labelbox.com/docs/polygon-json

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
        validator.validate(data)
        convert_with_path = partial(_convert, path=path)

        return list(map(convert_with_path, data))


# We ignore the Any | None warning here because the schema has been validated and we know
# we have the values with the correct types
def _convert(file_data: Dict[str, Any], path) -> AnnotationFile:
    filename: str = file_data.get("External ID")  # type: ignore
    label: Dict[str, Any] = file_data.get("Label")  # type: ignore
    label_objects: List[Dict[str, Any]] = label.get("objects")  # type: ignore

    annotations: List[Annotation] = list(map(_convert_label_objects, label_objects))
    classes: Set[AnnotationClass] = set(map(_get_class, annotations))
    return AnnotationFile(
        annotations=annotations, path=path, filename=filename, annotation_classes=classes, remote_path="/"
    )


def _convert_label_objects(obj: Dict[str, Any]) -> Annotation:
    title: str = str(obj.get("title"))
    bbox: Optional[Dict[str, Any]] = obj.get("bbox")
    if bbox:
        return _to_bbox_annotation(bbox, title)

    polygon: Optional[List[Point]] = obj.get("polygon")
    if polygon:
        return _to_polygon_annotation(polygon, title)

    raise ValueError(f"Unsupported object type {obj}")


def _to_bbox_annotation(bbox: Dict[str, Any], title: str) -> Annotation:
    x: float = cast(float, bbox.get("left"))
    y: float = cast(float, bbox.get("top"))
    width: float = cast(float, bbox.get("width"))
    height: float = cast(float, bbox.get("height"))

    return make_bounding_box(title, x, y, width, height)


def _to_polygon_annotation(polygon: List[Point], title: str) -> Annotation:
    return make_polygon(title, polygon, None)


def _get_class(annotation: Annotation) -> AnnotationClass:
    return annotation.annotation_class

