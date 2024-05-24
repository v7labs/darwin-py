from pathlib import Path
from typing import Callable, Dict, Iterable, List

from darwin.datatypes import AnnotationFile

ClassIndex = Dict[str, int]


def build_class_index(
    annotation_files: Iterable[AnnotationFile],
    include_types: List[str] = ["bounding_box", "polygon"],
) -> ClassIndex:
    classes = set()
    for annotation_file in annotation_files:
        for annotation in annotation_file.annotations:
            if annotation.annotation_class.annotation_type in include_types:
                classes.add(annotation.annotation_class.name)
    return {k: v for (v, k) in enumerate(sorted(classes))}


def export_file(
    annotation_file: AnnotationFile,
    class_index: ClassIndex,
    output_dir: Path,
    build_function: Callable[[AnnotationFile, ClassIndex], str],
) -> None:
    txt = build_function(annotation_file, class_index)

    # Just using `.with_suffix(".txt")` would remove all suffixes, so we need to
    # do it manually.

    filename = annotation_file.path.name
    filename_to_write = (
        filename.replace(".json", ".txt") if ".json" in filename else filename + ".txt"
    )
    output_file_path = output_dir / filename_to_write

    output_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file_path, "w") as f:
        f.write(txt)


def save_class_index(class_index: ClassIndex, output_dir: Path) -> None:
    sorted_items = sorted(class_index.items(), key=lambda item: item[1])

    with open(output_dir / "darknet.labels", "w") as f:
        for class_name, _ in sorted_items:
            f.write(f"{class_name}\n")
