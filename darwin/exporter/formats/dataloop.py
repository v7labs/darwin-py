from pathlib import Path
from typing import Any, Dict, Iterable

import deprecation
import orjson as json

import darwin.datatypes as dt
from darwin.exporter.formats.numpy_encoder import NumpyEncoder
from darwin.version import __version__

DEPRECATION_MESSAGE = """

This function is going to be turned into private. This means that breaking 
changes in its interface and implementation are to be expected. We encourage using ``export`` 
instead of calling this low-level function directly.

"""


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into the dataloop format inside of the given ``output_dir``.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new coco file will be.
    """
    for id, annotation_file in enumerate(annotation_files):
        _export_file(annotation_file, id, output_dir)


@deprecation.deprecated(
    deprecated_in="0.7.8",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def export_file(annotation_file: dt.AnnotationFile, id: int, output_dir: Path) -> None:
    output: Dict[str, Any] = _build_json(annotation_file, id)
    output_file_path: Path = (output_dir / annotation_file.filename).with_suffix(".json")
    with open(output_file_path, "w") as f:
        op = json.dumps(output, option=json.OPT_INDENT_2 | json.OPT_SERIALIZE_NUMPY).decode("utf-8")
        f.write(op)


@deprecation.deprecated(
    deprecated_in="0.7.8",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_json(annotation_file: dt.AnnotationFile, id: int) -> Dict[str, Any]:
    return {
        "_id": id,
        "filename": annotation_file.filename,
        "itemMetadata": [],
        "annotations": _build_annotations(annotation_file, id),
    }


@deprecation.deprecated(
    deprecated_in="0.7.8",
    removed_in="0.8.0",
    current_version=__version__,
    details=DEPRECATION_MESSAGE,
)
def build_annotations(annotation_file: dt.AnnotationFile, id: int) -> Iterable[Dict[str, Any]]:
    output = []
    for annotation_id, annotation in enumerate(annotation_file.annotations):
        print(annotation)
        if annotation.annotation_class.annotation_type == "bounding_box":
            entry = {
                "id": annotation_id,
                "datasetId": "darwin",
                "type": "box",
                "label": annotation.annotation_class.name,
                "attributes": [],
                "coordinates": [
                    {"x": annotation.data["x"], "y": annotation.data["y"], "z": 0},
                    {
                        "x": annotation.data["x"] + annotation.data["w"],
                        "y": annotation.data["y"] + annotation.data["h"],
                        "z": 0,
                    },
                ],
                "metadata": {},
            }
            output.append(entry)
        elif annotation.annotation_class.annotation_type == "polygon":
            entry = {
                "id": annotation_id,
                "datasetId": "darwin",
                "type": "segment",
                "label": annotation.annotation_class.name,
                "attributes": [],
                "coordinates": [{"x": point["x"], "y": point["y"], "z": 0} for point in annotation.data["path"]],
                "metadata": {},
            }
            output.append(entry)

    return output


def _export_file(annotation_file: dt.AnnotationFile, id: int, output_dir: Path) -> None:
    output: Dict[str, Any] = _build_json(annotation_file, id)
    output_file_path: Path = (output_dir / annotation_file.filename).with_suffix(".json")
    with open(output_file_path, "w") as f:
        op = json.dumps(output, option=json.OPT_INDENT_2 | json.OPT_SERIALIZE_NUMPY).decode("utf-8")
        f.write(op)


def _build_annotations(annotation_file: dt.AnnotationFile, id: int) -> Iterable[Dict[str, Any]]:
    output = []
    for annotation_id, annotation in enumerate(annotation_file.annotations):
        print(annotation)
        if annotation.annotation_class.annotation_type == "bounding_box":
            entry = {
                "id": annotation_id,
                "datasetId": "darwin",
                "type": "box",
                "label": annotation.annotation_class.name,
                "attributes": [],
                "coordinates": [
                    {"x": annotation.data["x"], "y": annotation.data["y"], "z": 0},
                    {
                        "x": annotation.data["x"] + annotation.data["w"],
                        "y": annotation.data["y"] + annotation.data["h"],
                        "z": 0,
                    },
                ],
                "metadata": {},
            }
            output.append(entry)
        elif annotation.annotation_class.annotation_type == "polygon":
            entry = {
                "id": annotation_id,
                "datasetId": "darwin",
                "type": "segment",
                "label": annotation.annotation_class.name,
                "attributes": [],
                "coordinates": [{"x": point["x"], "y": point["y"], "z": 0} for point in annotation.data["path"]],
                "metadata": {},
            }
            output.append(entry)

    return output


def _build_json(annotation_file: dt.AnnotationFile, id: int) -> Dict[str, Any]:
    return {
        "_id": id,
        "filename": annotation_file.filename,
        "itemMetadata": [],
        "annotations": _build_annotations(annotation_file, id),
    }
