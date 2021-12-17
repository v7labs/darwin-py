import json
from functools import partial, reduce
from os import listdir
from os.path import isdir, join
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, cast

from jsonschema import validate

from darwin.datatypes import Annotation, AnnotationClass, AnnotationFile, make_keypoint
from darwin.importer.formats.superannotate_schemas import (
    classes_export,
    superannotate_export,
)


def parse_path(path: Path) -> List[AnnotationFile]:
    """
    Parses SuperAnnotate annotations inside the given SuperAnnotate dataset folder and returns 
    the corresponding darwin annotations.
    Each annotation file must have a structure simillar to the following:
    
    .. code-block:: javascript
        {
            "instances": [
                {
                    "type": "point",
                    "x": 1,
                    "y": 0
                },
                // { ... }
            ],
            "metadata": {
                "name": "a_file_name.json"
            }
        }
    
    Currently we support the following annotations:

        - point ``Vector``: https://doc.superannotate.com/docs/vector-json#point
    

    Each folder much also have a ``classes.json`` file with information about the classes. This
    must have a structure simillar to:

    .. code-block:: javascript
        [
            {"name": "a_name_here", "id": 1},
            // { ... }
        ]

    You can check the SuperAnnotate Schemas in ``superannotate_schemas.py``.

    Parameters
    --------
    path: Path
        The path of the folder with the files to parse.
    
    Returns
    -------
    List[darwin.datatypes.AnnotationFile]
        The AnnotationFiles with the parsed information from each SuperAnnotate annotation inside 
        the folder.
    
    Raises
    ------
    ValidationError
        If any given JSON file is malformed or if it has an unknown annotation. 
        To see a list of possible annotation formats go to:
        https://doc.superannotate.com/docs/vector-json
    ValueError:
        If the given ``path`` is not a folder, or the given folder does not contain a 
        ``classes.json`` file inside.
    """
    if not isdir(path):
        raise ValueError("Path given must be a folder containing the annotations, images and 'classes.json' file.")

    classes_path = Path(join(path, "classes.json"))
    if not classes_path.is_file():
        raise ValueError("Folder must contain a 'classes.json' file with classes information.")

    map_to_path = partial(map, partial(_get_full_path, path))
    filter_by_annotations = partial(filter, _is_annotation)
    parse_annotation = partial(_parse_file, classes_file_path=classes_path)
    map_to_darwin_annotation = partial(map, parse_annotation)

    create_annotation_files = _composite_function(
        list, map_to_darwin_annotation, filter_by_annotations, map_to_path, listdir
    )
    return create_annotation_files(path)


def _parse_file(annotation_file_path: Path, classes_file_path: Path) -> AnnotationFile:
    with classes_file_path.open() as classes_file:
        classes = json.load(classes_file)
        validate(classes, schema=classes_export)

        with annotation_file_path.open() as annotation_file:
            data = json.load(annotation_file)
            validate(data, schema=superannotate_export)

            instances: List[Dict[str, Any]] = data.get("instances")
            metadata: Dict[str, Any] = data.get("metadata")

            return _convert(instances, annotation_file_path, classes, metadata)


def _convert(
    instances: List[Dict[str, Any]],
    annotation_file_path: Path,
    superannotate_classes: List[Dict[str, Any]],
    metadata: Dict[str, Any],
) -> AnnotationFile:
    filename: str = str(metadata.get("name"))

    convert_with_classes = partial(_convert_objects, superannotate_classes=superannotate_classes)
    annotations: List[Annotation] = _map_to_list(convert_with_classes, instances)
    classes: Set[AnnotationClass] = _map_to_set(_get_class, annotations)

    return AnnotationFile(
        annotations=annotations,
        path=annotation_file_path,
        filename=filename,
        annotation_classes=classes,
        remote_path="/",
    )


def _convert_objects(obj: Dict[str, Any], superannotate_classes: List[Dict[str, Any]]) -> Annotation:
    type: str = str(obj.get("type"))

    if type == "point":
        return _to_keypoint_annotation(obj, superannotate_classes)

    raise ValueError(f"Unknown label object {obj}")


def _to_keypoint_annotation(point: Dict[str, Any], classes: List[Dict[str, Any]]) -> Annotation:
    x: float = cast(float, point.get("x"))
    y: float = cast(float, point.get("y"))
    class_id: int = cast(int, point.get("classId"))

    name = _find_class_name(class_id, classes)
    return make_keypoint(name, x, y)


def _find_class_name(class_id: int, classes: List[Dict[str, Any]]) -> str:
    obj: Optional[Dict[str, Any]] = next((class_obj for class_obj in classes if class_obj.get("id") == class_id), None)

    if obj is None:
        raise ValueError(
            f"No class with id '{class_id}' was found in {classes}.\nCannot continue import, pleaase check your 'classes.json' file."
        )

    return str(obj.get("name"))


def _get_class(annotation: Annotation) -> AnnotationClass:
    return annotation.annotation_class


def _map_to_list(fun: Callable[[Any], Any], the_list: List[Any]) -> List[Any]:
    return list(map(fun, the_list))


def _map_to_set(fun: Callable[[Any], Any], iter: Iterable[Any]) -> Set[Any]:
    return set(map(fun, iter))


def _get_full_path(dir: Path, file: str) -> Path:
    return Path(join(dir, file))


def _is_annotation(file: Path) -> bool:
    return file.suffix == ".json" and file.name != "classes.json"


def _composite_function(*func):
    def compose(f, g):
        return lambda x: f(g(x))

    return reduce(compose, func, lambda x: x)

