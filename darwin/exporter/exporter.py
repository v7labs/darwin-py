import json
from pathlib import Path
from typing import Callable, Generator, List, Union

import darwin.datatypes as dt


def _parse_darwin_json(path: Path, count: int):
    with path.open() as f:
        data = json.load(f)
        if not data["annotations"]:
            return None
        annotations = list(filter(None, map(_parse_darwin_annotation, data["annotations"])))
        annotation_classes = set([annotation.annotation_class for annotation in annotations])

        return dt.AnnotationFile(
            path,
            data["image"]["original_filename"],
            annotation_classes,
            annotations,
            data["image"]["width"],
            data["image"]["height"],
            data["image"]["url"],
            data["image"].get("workview_url"),
            data["image"].get("seq", count),
        )


def _parse_darwin_annotation(annotation):
    name = annotation["name"]
    main_annotation = None
    if "polygon" in annotation:
        main_annotation = dt.make_polygon(name, annotation["polygon"]["path"])
    elif "bounding_box" in annotation:
        bounding_box = annotation["bounding_box"]
        main_annotation = dt.make_bounding_box(
            name, bounding_box["x"], bounding_box["y"], bounding_box["w"], bounding_box["h"],
        )
    elif "tag" in annotation:
        main_annotation = dt.make_tag(name)

    if not main_annotation:
        print(f"[WARNING] Unsupported annotation type: '{annotation.keys()}'")
        return None

    if "instance_id" in annotation:
        main_annotation.subs.append(dt.make_instance_id(annotation["instance_id"]["value"]))
    if "attributes" in annotation:
        main_annotation.subs.append(dt.make_attributes(annotation["attributes"]))
    if "text" in annotation:
        main_annotation.subs.append(dt.make_text(annotation["text"]["text"]))

    return main_annotation


def darwin_to_dt_gen(file_paths):
    count = 0
    for file_path in map(Path, file_paths):
        files = file_path.glob("**/*") if file_path.is_dir() else [file_path]
        for f in files:
            if f.suffix != ".json":
                continue
            data = _parse_darwin_json(f, count)
            if data:
                yield data
            count += 1


def export_annotations(
    exporter: Callable[[Generator[dt.AnnotationFile, None, None], Path], None],
    file_paths: List[Union[str, Path]],
    output_directory: Union[str, Path],
):
    """Converts a set of files to a different annotation format"""
    exporter(darwin_to_dt_gen(file_paths), Path(output_directory))
