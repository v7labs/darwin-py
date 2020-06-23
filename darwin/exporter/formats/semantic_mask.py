from pathlib import Path
from typing import Generator, List

import numpy as np
from PIL import Image
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_sequences, get_progress_bar, ispolygon


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path, mode: str = "grayscale"):
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)

    categories = calculate_categories(annotation_files)
    if mode == "index":
        palette = {c: i for i, c in enumerate(categories)}
    elif mode == "grayscale":
        palette = {c: int(i * 255 / (len(categories)-1)) for i, c in enumerate(categories)}
    elif mode == "rgb":
        raise NotImplementedError

    for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
        outfile = masks_dir / f"{annotation_file.path.stem}.png"
        height = annotation_file.image_height
        width = annotation_file.image_width
        mask = np.zeros((height, width)).astype(np.uint8)
        annotations = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
        for a in annotations:
            cat = a.annotation_class.name
            if a.annotation_class.annotation_type == "polygon":
                polygon = a.data["path"]
            elif a.annotation_class.annotation_type == "complex_polygon":
                polygon = a.data["paths"]
            sequence = convert_polygons_to_sequences(polygon, height=height, width=width)
            draw_polygon(mask, sequence, palette[cat])
        mask = Image.fromarray(mask)
        mask.save(outfile)

    with open(output_dir / "class_mapping.csv", "w") as f:
        f.write(f"class_idx,class_name\n")
        for c in categories:
            f.write(f"{palette[c]},{c}\n")


def calculate_categories(annotation_files: List[dt.AnnotationFile]):
    categories = set()
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if ispolygon(annotation_class):
                categories.add(annotation_class.name)
    categories = list(categories)
    categories.sort()
    categories.insert(0, "__background__")
    return categories
