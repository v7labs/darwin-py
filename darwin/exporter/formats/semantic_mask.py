import colorsys
import os
from pathlib import Path
from typing import Generator, List

import numpy as np
from PIL import Image
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_sequences, get_progress_bar, ispolygon


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path, mode: str = "grey"):
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)

    categories = extract_categories(annotation_files)
    N = len(categories)
    if mode == "index":
        if N > 254:
            raise ValueError("maximum number of classes supported: 254")
        palette = {c: i for i, c in enumerate(categories)}
    elif mode == "grey":
        if N > 254:
            raise ValueError("maximum number of classes supported: 254")
        palette = {c: int(i * 255 / (N - 1)) for i, c in enumerate(categories)}
    elif mode == "rgb":
        if N > 360:
            raise ValueError("maximum number of classes supported: 360")
        palette = {c: i for i, c in enumerate(categories)}
        HSV_colors = [(x / N, 0.8, 1.0) for x in range(N - 1)]  # Generate HSV colors for all classes except for BG
        RGB_colors = list(map(lambda x: [int(e * 255) for e in colorsys.hsv_to_rgb(*x)], HSV_colors))
        RGB_colors.insert(0, [0, 0, 0])  # Now we add BG class with [0 0 0] RGB value
        palette_rgb = {c: rgb for c, rgb in zip(categories, RGB_colors)}
        RGB_colors = [c for e in RGB_colors for c in e]

    for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
        image_id = os.path.splitext(annotation_file.filename)[0]
        outfile = masks_dir / f"{image_id}.png"
        outfile.parent.mkdir(parents=True, exist_ok=True)
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
        if mode == "rgb":
            mask = Image.fromarray(mask, "P")
            mask.putpalette(RGB_colors)
        else:
            mask = Image.fromarray(mask)
        mask.save(outfile)

    with open(output_dir / "class_mapping.csv", "w") as f:
        f.write(f"class_name,class_color\n")
        for c in categories:
            if mode == "rgb":
                f.write(f"{c},{palette_rgb[c][0]} {palette_rgb[c][1]} {palette_rgb[c][2]}\n")
            else:
                f.write(f"{c},{palette[c]}\n")


def extract_categories(annotation_files: List[dt.AnnotationFile]):
    categories = set()
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if ispolygon(annotation_class):
                categories.add(annotation_class.name)
    categories = list(categories)
    categories.sort()
    categories.insert(0, "__background__")
    return categories
