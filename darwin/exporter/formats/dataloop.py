import json
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator

import darwin.datatypes as dt
from darwin.exporter.formats.numpy_encoder import NumpyEncoder


def export(annotation_files: Iterator[dt.AnnotationFile], output_dir: Path) -> None:
    for id, annotation_file in enumerate(annotation_files):
        export_file(annotation_file, id, output_dir)


def export_file(annotation_file: dt.AnnotationFile, id: int, output_dir: Path) -> None:
    output: Dict[str, Any] = build_json(annotation_file, id)
    output_file_path: Path = (output_dir / annotation_file.filename).with_suffix(".json")
    with open(output_file_path, "w") as f:
        json.dump(output, f, cls=NumpyEncoder, indent=1)


def build_json(annotation_file: dt.AnnotationFile, id: int) -> Dict[str, Any]:
    return {
        "_id": id,
        "filename": annotation_file.filename,
        "itemMetadata": [],
        "annotations": build_annotations(annotation_file, id),
    }


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
