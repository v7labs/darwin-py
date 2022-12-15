from functools import partial
from itertools import zip_longest
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Union, cast

import orjson as json
from jsonschema import validate

from darwin.datatypes import (
    Annotation,
    AnnotationClass,
    AnnotationFile,
    CuboidData,
    Point,
    SubAnnotation,
    make_attributes,
    make_bounding_box,
    make_cuboid,
    make_ellipse,
    make_keypoint,
    make_line,
    make_polygon,
    make_tag,
)
from darwin.importer.formats.superannotate_schemas import (
    classes_export,
    superannotate_export,
)

AttributeGroup = Dict[str, Union[str, int]]


def parse_path(path: Path) -> Optional[AnnotationFile]:
    """
    Parses SuperAnnotate annotations inside the given file and returns the corresponding Darwin JSON
    annotations. If the given file is not a ``.json`` or is a ``classes.json`` then ``None`` is
    returned instead.

    Each annotation file must have a structure similar to the following:

    .. code-block:: javascript

        {
            "instances": [
                {
                    "classId": 1,
                    "attributes": [],
                    "type": "point",
                    "x": 1,
                    "y": 0
                },
                // { ... }
            ],
            "tags": ["a_tag_here"],
            "metadata": {
                "name": "a_file_name.json"
            }
        }

    Currently we support the following annotations:

        - point ``Vector``: https://doc.superannotate.com/docs/vector-json#point
        - ellipse ``Vector``: https://doc.superannotate.com/docs/vector-json#ellipse
        - cuboid ``Vector``: https://doc.superannotate.com/docs/vector-json#cuboid
        - bbox ``Vector`` (not rotated): https://doc.superannotate.com/docs/vector-json#bounding-box-and-rotated-bounding-box
        - polygon and polyline ``Vector``\\s: https://doc.superannotate.com/docs/vector-json#polyline-and-polygon

    We also support attributes and tags.

    Each file must also have in the same folder a ``classes.json`` file with information about
    the classes. This file must have a structure similar to:

    .. code-block:: javascript

        [
            {"name": "a_name_here", "id": 1, "attribute_groups": []},
            // { ... }
        ]

    You can check the SuperAnnotate Schemas in ``superannotate_schemas.py``.

    Parameters
    --------
    path: Path
        The path of the file to parse.

    Returns
    -------
    Optional[darwin.datatypes.AnnotationFile]
        The AnnotationFile with the parsed information from each SuperAnnotate annotation inside
        or ``None`` if the given file is not a ``.json`` or is ``classes.json``.

    Raises
    ------
    ValidationError
        If any given JSON file is malformed or if it has an unknown annotation.
        To see a list of possible annotation formats go to:
        https://doc.superannotate.com/docs/vector-json
    """

    if not _is_annotation(path):
        return None

    classes_path = path.parent / "classes.json"
    if not classes_path.is_file():
        raise ValueError("Folder must contain a 'classes.json' file with classes information.")

    with classes_path.open() as classes_file:
        classes = json.loads(classes_file.read())
        validate(classes, schema=classes_export)

    with path.open() as annotation_file:
        data = json.loads(annotation_file.read())
        validate(data, schema=superannotate_export)

        instances: List[Dict[str, Any]] = data.get("instances")
        metadata: Dict[str, Any] = data.get("metadata")
        tags: List[str] = data.get("tags")

        return _convert(instances, path, classes, metadata, tags)


def _convert(
    instances: List[Dict[str, Any]],
    annotation_file_path: Path,
    superannotate_classes: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    tags: List[str],
) -> AnnotationFile:
    conver_to_darwin_object = partial(_convert_instance, superannotate_classes=superannotate_classes)

    filename: str = str(metadata.get("name"))
    darwin_tags: List[Annotation] = _map_to_list(make_tag, tags)
    darwin_objects: List[Annotation] = _map_to_list(conver_to_darwin_object, instances)
    annotations: List[Annotation] = darwin_objects + darwin_tags
    classes: Set[AnnotationClass] = _map_to_set(_get_class, annotations)

    return AnnotationFile(
        annotations=annotations,
        path=annotation_file_path,
        filename=filename,
        annotation_classes=classes,
        remote_path="/",
    )


def _convert_instance(obj: Dict[str, Any], superannotate_classes: List[Dict[str, Any]]) -> Annotation:
    type: str = str(obj.get("type"))

    if type == "point":
        return _to_keypoint_annotation(obj, superannotate_classes)

    if type == "ellipse":
        return _to_ellipse_annotation(obj, superannotate_classes)

    if type == "cuboid":
        return _to_cuboid_annotation(obj, superannotate_classes)

    if type == "bbox":
        return _to_bbox_annotation(obj, superannotate_classes)

    if type == "polygon":
        return _to_polygon_annotation(obj, superannotate_classes)

    if type == "polyline":
        return _to_line_annotation(obj, superannotate_classes)

    raise ValueError(f"Unknown label object {obj}")


def _to_keypoint_annotation(point: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    x: float = cast(float, point.get("x"))
    y: float = cast(float, point.get("y"))
    class_id: int = cast(int, point.get("classId"))

    instance_class: Dict[str, Any] = _find_class(class_id, classes)
    name: str = str(instance_class.get("name"))
    attributes: Optional[SubAnnotation] = _get_attributes(point, instance_class)
    subannotations: Optional[List[SubAnnotation]] = None
    if attributes:
        subannotations = [attributes]
    return make_keypoint(f"{name}-point", x, y, subannotations)


def _to_bbox_annotation(bbox: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    points: Dict[str, float] = cast(Dict[str, float], bbox.get("points"))
    x: float = cast(float, points.get("x1"))
    y: float = cast(float, points.get("y1"))
    w: float = abs(cast(float, points.get("x2")) - cast(float, points.get("x1")))
    h: float = abs(cast(float, points.get("y1")) - cast(float, points.get("y2")))
    class_id: int = cast(int, bbox.get("classId"))

    instance_class: Dict[str, Any] = _find_class(class_id, classes)
    name: str = str(instance_class.get("name"))
    attributes: Optional[SubAnnotation] = _get_attributes(bbox, instance_class)
    subannotations: Optional[List[SubAnnotation]] = None
    if attributes:
        subannotations = [attributes]

    return make_bounding_box(f"{name}-bbox", x, y, w, h, subannotations)


def _to_ellipse_annotation(ellipse: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    angle: float = cast(float, ellipse.get("angle"))
    center: Point = {"x": cast(float, ellipse.get("cx")), "y": cast(float, ellipse.get("cy"))}
    radius: Point = {"x": cast(float, ellipse.get("rx")), "y": cast(float, ellipse.get("ry"))}
    ellipse_data: Dict[str, Union[float, Point]] = {"angle": angle, "center": center, "radius": radius}
    class_id: int = cast(int, ellipse.get("classId"))

    instance_class: Dict[str, Any] = _find_class(class_id, classes)
    name: str = str(instance_class.get("name"))
    attributes: Optional[SubAnnotation] = _get_attributes(ellipse, instance_class)
    subannotations: Optional[List[SubAnnotation]] = None
    if attributes:
        subannotations = [attributes]

    return make_ellipse(f"{name}-ellipse", ellipse_data, subannotations)


def _to_cuboid_annotation(cuboid: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    points: Dict[str, Dict[str, float]] = cast(Dict[str, Dict[str, float]], cuboid.get("points"))
    back_top_left_point: Dict[str, float] = cast(Dict[str, float], points.get("r1"))
    back_bottom_right_point: Dict[str, float] = cast(Dict[str, float], points.get("r2"))
    front_top_left_point: Dict[str, float] = cast(Dict[str, float], points.get("f1"))
    front_bottom_right_point: Dict[str, float] = cast(Dict[str, float], points.get("f2"))

    cuboid_data: CuboidData = {
        "back": {
            "h": abs(cast(float, back_top_left_point.get("y")) - cast(float, back_bottom_right_point.get("y"))),
            "w": abs(cast(float, back_bottom_right_point.get("x")) - cast(float, back_top_left_point.get("x"))),
            "x": cast(float, back_top_left_point.get("x")),
            "y": cast(float, back_top_left_point.get("y")),
        },
        "front": {
            "h": abs(cast(float, front_top_left_point.get("y")) - cast(float, front_bottom_right_point.get("y"))),
            "w": abs(cast(float, front_bottom_right_point.get("x")) - cast(float, front_top_left_point.get("x"))),
            "x": cast(float, front_top_left_point.get("x")),
            "y": cast(float, front_top_left_point.get("y")),
        },
    }
    class_id: int = cast(int, cuboid.get("classId"))

    instance_class: Dict[str, Any] = _find_class(class_id, classes)
    name: str = str(instance_class.get("name"))
    attributes: Optional[SubAnnotation] = _get_attributes(cuboid, instance_class)
    subannotations: Optional[List[SubAnnotation]] = None
    if attributes:
        subannotations = [attributes]

    return make_cuboid(f"{name}-cuboid", cuboid_data, subannotations)


def _to_polygon_annotation(polygon: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    data: List[float] = cast(List[float], polygon.get("points"))
    class_id: int = cast(int, polygon.get("classId"))
    instance_class: Dict[str, Any] = _find_class(class_id, classes)
    name: str = str(instance_class.get("name"))
    points: List[Point] = _map_to_list(_tuple_to_point, _group_to_list(data, 2, 0))

    attributes: Optional[SubAnnotation] = _get_attributes(polygon, instance_class)
    subannotations: Optional[List[SubAnnotation]] = None
    if attributes:
        subannotations = [attributes]
    return make_polygon(f"{name}-polygon", points, None, subannotations)


def _to_line_annotation(line: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    data: List[float] = cast(List[float], line.get("points"))
    class_id: int = cast(int, line.get("classId"))
    instance_class: Dict[str, Any] = _find_class(class_id, classes)
    name: str = str(instance_class.get("name"))
    points: List[Point] = _map_to_list(_tuple_to_point, _group_to_list(data, 2, 0))
    attributes: Optional[SubAnnotation] = _get_attributes(line, instance_class)
    subannotations: Optional[List[SubAnnotation]] = None
    if attributes:
        subannotations = [attributes]

    return make_line(f"{name}-polyline", points, subannotations)


def _find_class(class_id: int, classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    obj: Optional[Dict[str, Any]] = next((class_obj for class_obj in classes if class_obj.get("id") == class_id), None)

    if obj is None:
        raise ValueError(
            f"No class with id '{class_id}' was found in {classes}.\nCannot continue import, pleaase check your 'classes.json' file."
        )

    return obj


def _get_attributes(instance: Dict[str, Any], instance_class: Dict[str, Any]) -> Optional[SubAnnotation]:
    attribute_info: List[Dict[str, int]] = cast(List[Dict[str, int]], instance.get("attributes"))
    groups: List[Dict[str, Any]] = cast(List[Dict[str, Any]], instance_class.get("attribute_groups"))
    all_attributes: List[str] = []

    for info in attribute_info:
        info_group_id: int = cast(int, info.get("groupId"))
        attribute_id: int = cast(int, info.get("id"))

        for group in groups:
            group_id: int = cast(int, group.get("id"))

            if info_group_id != group_id:
                continue

            group_attributes: List[AttributeGroup] = cast(List[AttributeGroup], group.get("attributes"))
            attribute: Optional[AttributeGroup] = next(
                (attribute for attribute in group_attributes if attribute.get("id") == attribute_id), None
            )

            if attribute is None:
                raise ValueError(f"No attribute data found for {info}.")

            final_attribute: str = f"{str(group.get('name'))}:{str(attribute.get('name'))}"
            all_attributes.append(final_attribute)

    if all_attributes == []:
        return None

    return make_attributes(all_attributes)


def _get_class(annotation: Annotation) -> AnnotationClass:
    return annotation.annotation_class


def _map_to_list(fun: Callable[[Any], Any], the_list: List[Any]) -> List[Any]:
    return list(map(fun, the_list))


def _map_to_set(fun: Callable[[Any], Any], iter: Iterable[Any]) -> Set[Any]:
    return set(map(fun, iter))


def _is_annotation(file: Path) -> bool:
    return file.suffix == ".json" and file.name != "classes.json"


def _tuple_to_point(tuple) -> Dict[str, float]:
    return {"x": tuple[0], "y": tuple[1]}


# Inspired by: https://stackoverflow.com/a/434411/1337392
def _group_to_list(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return list(zip_longest(*args, fillvalue=fillvalue))
