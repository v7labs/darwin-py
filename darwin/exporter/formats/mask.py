import colorsys
import os
from pathlib import Path
from typing import Dict, Iterable, List, Set

import numpy as np
from PIL import Image
from upolygon import draw_polygon, rle_decode

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_sequences, ispolygon

PalleteType = Dict[str, int]


def get_palette(mode: str, categories: List[str]) -> PalleteType:
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


def get_render_mode(annotations: List[dt.AnnotationLike]) -> str:
    keys: Set[str] = set([a.data.keys() for a in annotations])

    is_raster_mask = "mask" in keys and "raster_layer" in keys
    is_polygon = "polygon" in keys or "complex_polygon" in keys

    if is_raster_mask and is_polygon:
        raise ValueError("Cannot have both raster and polygon annotations in the same file")

    if is_raster_mask:
        return "raster"
    if is_polygon:
        return "polygon"

    raise ValueError("No renderable annotations found in file, found keys: " + ",".join(keys))


def render_polygons(
    mask: Image.Image,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,
    height: int,
    width: int,
    palette: PalleteType,
) -> Image.Image:
    for a in annotations:
        if isinstance(a, dt.VideoAnnotation):
            print(f"Skipping video annotation from file {annotation_file.filename}")
            continue

        cat = a.annotation_class.name
        if a.annotation_class.annotation_type == "polygon":
            polygon = a.data["path"]
        elif a.annotation_class.annotation_type == "complex_polygon":
            polygon = a.data["paths"]
        sequence = convert_polygons_to_sequences(polygon, height=height, width=width)
        mask = draw_polygon(mask, sequence, palette[cat])

    # It's not necessary to return the mask, it's modified in place, but it's more explicit
    return mask


def render_raster(
    mask: Image.Image,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,
    height: int,
    width: int,
    palette: PalleteType,
) -> Image.Image:
    errors: List[Exception] = []
    for a in annotations:
        if isinstance(a, dt.VideoAnnotation):
            print(f"Skipping video annotation from file {annotation_file.filename}")
            continue

        cat = a.annotation_class.name
        if a.annotation_class.annotation_type == "raster": #TODO implement render raster type
            name = a.data.get("name")
            raster = a.data.get("raster_layer")
            if not raster:
                errors.append(ValueError(f"Annotation {name} has no raster layer"))
                continue

            rle = raster.get("rle")
            if not rle:
                errors.append(ValueError(f"Annotation {name} has no RLE data"))
                continue

            
        else:
            


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
        # TODO
        # Identify if we have masks and raster or polygons
        # If we have masks and raster, we need to calculate and render an image from that
        # If we have polygons, we need to render the polygons into an image
        # If we have masks and polygons, we need to render the polygons into an image
        image_rel_path = os.path.splitext(annotation_file.full_path)[0].lstrip("/")
        outfile = masks_dir / f"{image_rel_path}.png"
        outfile.parent.mkdir(parents=True, exist_ok=True)

        height = annotation_file.image_height
        width = annotation_file.image_width
        if height is None or width is None:
            raise ValueError(f"Annotation file {annotation_file.filename} references an image with no height or width")

        mask: Image.Image = np.zeros((height, width)).astype(np.uint8)  # type: ignore
        annotations: List[dt.AnnotationLike] = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]

        mode = get_render_mode(annotations)

        if mode == "raster":
            # TODO: implement this - render the raster
            raise NotImplementedError("Raster masks are not yet supported")

        else:
            for a in annotations:
                if isinstance(a, dt.VideoAnnotation):
                    print(f"Skipping video annotation from file {annotation_file.filename}")
                    continue

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
