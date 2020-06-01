import json

import numpy as np

import darwin.datatypes as dt


class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)


def export(annotation_files, output_dir):
    for id, annotation_file in enumerate(annotation_files):
        export_file(annotation_file, id, output_dir)


def export_file(annotation_file, id, output_dir):
    output = build_json(annotation_file, id)
    output_file_path = (output_dir / annotation_file.filename).with_suffix(".json")
    with open(output_file_path, "w") as f:
        json.dump(output, f, cls=NumpyEncoder, indent=1)


def build_json(annotation_file: dt.AnnotationFile, id):
    return {
        "_id": id,
        "filename": annotation_file.filename,
        "itemMetadata": [],
        "annotations": build_annotations(annotation_file, id),
    }


def build_annotations(annotation_file: dt.AnnotationFile, id):
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
    #   elif annotation.annotation_class.name == "bounding_box":
    return output
