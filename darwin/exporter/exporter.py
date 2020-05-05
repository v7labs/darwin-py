import json
from pathlib import Path
from typing import Callable, List, Union

import darwin.datatypes as dt
from darwin.client import Client
from darwin.exporter.formats.pascalvoc import export_file


def _parse_darwin_json(path: Path):
    with path.open() as f:
        data = json.load(f)
        annotations = list(
            filter(None, map(_parse_darwin_annotation, data["annotations"]))
        )
        annotation_classes = set(
            [annotation.annotation_class for annotation in annotations]
        )

        return dt.AnnotationFile(
            path,
            data["image"]["original_filename"],
            annotation_classes,
            annotations,
            data["image"]["width"],
            data["image"]["height"],
        )


def _parse_darwin_annotation(annotation):
    name = annotation["name"]
    if "polygon" in annotation:
        return dt.make_polygon(name, annotation["polygon"])
    elif "bounding_box" in annotation:
        bounding_box = annotation["bounding_box"]
        return dt.make_bounding_box(
            name,
            bounding_box["x"],
            bounding_box["y"],
            bounding_box["w"],
            bounding_box["h"],
        )
    elif "tag" in annotation:
        return dt.make_tag(name)
    else:
        raise ValueError(f"Unsupported annotation type: '{annotation.keys()}'")


def export_annotations(
    client: "Client",
    exporter: Callable[[dt.AnnotationFile, Path], None],
    file_paths: List[Union[str, Path]],
    output_directory: Union[str, Path],
):
    """Converts a set of files to a different annotation format"""
    for file_path in map(Path, file_paths):
        files = file_path.glob("**/*") if file_path.is_dir() else [file_path]
        for f in files:
            if f.suffix != ".json":
                continue
            darwin_annotation_file = _parse_darwin_json(f)
            exporter(darwin_annotation_file, Path(output_directory))
