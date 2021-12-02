import json
from functools import partial, reduce
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, cast

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    Point,
    make_bounding_box,
    make_keypoint,
    make_line,
    make_polygon,
    make_tag,
)


def parse_file(path: Path, validate: Callable[[Any], None]) -> Optional[List[AnnotationFile]]:
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
                ],
                "classifications": [
                    {
                        "value": "a_question",
                        "answer": {"value": "an_answer"}
                    },
                    ....
                ]
            },
            "External ID": "demo-image-7.jpg"
        },
        {...}
    ]
    ```

    You can check the Labelbox Schemas in `labelbox_schemas.py`.

    Currently we support the following annotations:
    - bounding-box `Image`: https://docs.labelbox.com/docs/bounding-box-json
    - polygon `Image`: https://docs.labelbox.com/docs/polygon-json
    - point `Image`: https://docs.labelbox.com/docs/point-json
    - polyline `Image`: https://docs.labelbox.com/docs/polyline-json

    We also support conversion from question/answer to Annotation Tags for the following:
    - Radio Buttons
    - Multiple Choice

    Parameters
    --------
    path: Path
        The path of the file to parse.

    validate: Callable[[Any], None]
        The validator function that validates the schema.

    Returns
    -------
    Optional[List[darwin.datatypes.AnnotationFile]]
        The AnnotationFiles with the parsed information from the file or None, if the file is not a 
        `json` file.

    Raises
    ------
    ValidationError
        If the given JSON file is malformed or if it has an unknown annotation. 
        To see a list of possible annotation formats go to:
        https://docs.labelbox.com/docs/annotation-types-1

    """
    if path.suffix != ".json":
        return None

    with path.open() as f:
        data = json.load(f)
        validate(data)
        convert_with_path = partial(_convert, path=path)

        return list(map(convert_with_path, data))


def _convert(file_data: Dict[str, Any], path) -> AnnotationFile:
    filename: str = str(file_data.get("External ID"))
    label: Dict[str, Any] = cast(Dict[str, Any], file_data.get("Label"))
    label_objects: List[Dict[str, Any]] = cast(List[Dict[str, Any]], label.get("objects"))
    label_classifications: List[Dict[str, Any]] = cast(List[Dict[str, Any]], label.get("classifications"))

    classification_annotations: List[Annotation] = []
    if label_classifications != []:
        # We do a flat_map here: https://stackoverflow.com/a/2082107/1337392
        classification_annotations = reduce(list.__add__, map(_convert_label_classifications, label_classifications))

    object_annotations: List[Annotation] = list(map(_convert_label_objects, label_objects))
    annotations: List[Annotation] = object_annotations + classification_annotations

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

    point: Optional[Point] = obj.get("point")
    if point:
        return _to_keypoint_annotation(point, title)

    line: Optional[List[Point]] = obj.get("line")
    if line:
        return _to_line_annotation(line, title)


def _convert_label_classifications(obj: Dict[str, Any]) -> List[Annotation]:
    question: str = str(obj.get("value"))

    radio_button: Optional[Dict[str, Any]] = obj.get("answer")
    if radio_button is not None:
        return [_to_tag_annotations_from_radio_box(question, radio_button)]

    multiple_choice: Optional[List[Dict[str, Any]]] = obj.get("answers")
    if multiple_choice is not None:
        return _to_tag_annotations_from_multiple_choice(question, multiple_choice)


def _to_bbox_annotation(bbox: Dict[str, Any], title: str) -> Annotation:
    x: float = cast(float, bbox.get("left"))
    y: float = cast(float, bbox.get("top"))
    width: float = cast(float, bbox.get("width"))
    height: float = cast(float, bbox.get("height"))

    return make_bounding_box(title, x, y, width, height)


def _to_polygon_annotation(polygon: List[Point], title: str) -> Annotation:
    return make_polygon(title, polygon, None)


def _to_keypoint_annotation(point: Point, title: str) -> Annotation:
    x: float = cast(float, point.get("x"))
    y: float = cast(float, point.get("y"))

    return make_keypoint(title, x, y)


def _to_line_annotation(line: List[Point], title: str) -> Annotation:
    return make_line(title, line, None)


def _to_tag_annotations_from_radio_box(question: str, radio_button: Dict[str, Any]) -> Annotation:
    answer: str = str(radio_button.get("value"))
    return make_tag(f"{question}:{answer}")


def _to_tag_annotations_from_multiple_choice(question: str, multiple_choice) -> List[Annotation]:
    annotations: List[Annotation] = []
    for answer in multiple_choice:
        val: str = answer.get("value")
        annotations.append(make_tag(f"{question}:{val}"))

    return annotations


def _get_class(annotation: Annotation) -> AnnotationClass:
    return annotation.annotation_class

