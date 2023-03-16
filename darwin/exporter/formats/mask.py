import colorsys
import os
from pathlib import Path
from typing import Dict, Iterable, List, Set

import numpy as np
from PIL import Image
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_sequences, ispolygon


def get_palette(mode: str, categories: List[str]) -> Dict[str, int]:
    num_categories: int = len(categories)
    if mode == "index":
        if num_categories > 254:
            raise ValueError("maximum number of classes supported: 254.")
        return {c: i for i, c in enumerate(categories)}

    if mode == "grey":
        if num_categories > 254:
            raise ValueError("maximum number of classes supported: 254.")
        elif num_categories == 1:
            raise ValueError("only having the '__background__' class is not allowed. Please add more classes.")

        return {c: int(i * 255 / (num_categories - 1)) for i, c in enumerate(categories)}

    if mode == "rgb":
        if num_categories > 360:
            raise ValueError("maximum number of classes supported: 360.")
        return {c: i for i, c in enumerate(categories)}

    raise ValueError(f"Unknown mode {mode}.")


def validate_annotations(annotations: List[dt.AnnotationLike]) -> None:
    types_in_annotations: Set[str] = set([a.annotation_class.annotation_type for a in annotations])
    if "raster_layer" in types_in_annotations and "mask" in types_in_annotations:
        raise ValueError(f"Annotation file contains both mask and raster layer annotations. This is not supported.")


def _handle_mask(annotation: dt.Annotation) -> Image.Image:
    ...


def _handle_raster_layer(annotation: dt.Annotation) -> Image.Image:
    ...


def _handle_polygon(
    annotation: dt.Annotation, height: int, width: int, mask: np.ndarray, cat: str, palette: Dict[str, int]
) -> Image.Image:
    type: str = annotation.annotation_class.annotation_type
    polygon = annotation.data["path"] if type == "polygon" else annotation.data["paths"]
    sequence = convert_polygons_to_sequences(polygon, height=height, width=width)
    mask = draw_polygon(mask, sequence, palette[cat])

    return mask  # It's not actually necessary to return the mask, as it's modified in place, but it's a good practice


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path, mode: str) -> None:
    masks_dir: Path = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)

    categories: List[str] = extract_categories(annotation_files)
    num_categories = len(categories)

    palette = get_palette(mode=mode, categories=categories)
    if mode == "rgb":
        # Generate HSV colors for all classes except for BG
        HSV_colors = [(x / num_categories, 0.8, 1.0) for x in range(num_categories - 1)]
        RGB_color_list = list(map(lambda x: [int(e * 255) for e in colorsys.hsv_to_rgb(*x)], HSV_colors))
        # Now we add BG class with [0 0 0] RGB value
        RGB_color_list.insert(0, [0, 0, 0])
        palette_rgb = {c: rgb for c, rgb in zip(categories, RGB_color_list)}
        RGB_colors = [c for e in RGB_color_list for c in e]

    for annotation_file in annotation_files:
        image_rel_path = os.path.splitext(annotation_file.full_path)[0].lstrip("/")
        outfile = masks_dir / f"{image_rel_path}.png"
        outfile.parent.mkdir(parents=True, exist_ok=True)

        height = annotation_file.image_height
        width = annotation_file.image_width
        if height is None or width is None:
            raise ValueError(f"Annotation file {annotation_file.filename} references an image with no height or width")

        mask: Image.Image = np.zeros((height, width)).astype(np.uint8)
        annotations: List[dt.AnnotationLike] = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
        validate_annotations(annotations)

        for a in annotations:
            if isinstance(a, dt.VideoAnnotation):
                print(f"Skipping video annotation from file {annotation_file.filename}")
                continue

            cat = a.annotation_class.name
            if annotation_type := a.annotation_class.annotation_type in ["polygon", "complex_polygon"]:
                # Polygon rendering
                mask = _handle_polygon(a, height, width, mask, cat, palette)

            elif annotation_type == "mask":
                # Mask sparse rle rendering
                mask = _handle_mask(a, mask)

            elif annotation_type == "raster_layer":
                # Raster layer dense RLE rendering
                mask = _handle_raster_layer(a, mask)

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


def extract_categories(annotation_files: List[dt.AnnotationFile]) -> List[str]:
    categories = set()
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if ispolygon(annotation_class):
                categories.add(annotation_class.name)

    result = list(categories)
    result.sort()
    result.insert(0, "__background__")

    return result
