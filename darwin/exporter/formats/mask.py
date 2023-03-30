import colorsys
import os
from functools import reduce
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Set, Tuple, get_args

import numpy as np
from PIL.Image import Image
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.exceptions import DarwinException
from darwin.utils import convert_polygons_to_sequences, ispolygon

Palette = Dict[str, int]
Mode = Literal["index", "grey", "rgb"]
TypeOfRender = Literal["raster", "polygon"]
CategoryList = List[str]
ExceptionList = List[dt.AnnotationLike]
UndecodedRLE = List[int]
DecodedRLE = List[List[int]]


def get_palette(mode: Mode, categories: List[str]) -> Palette:
    """
    Returns a palette for the given mode and categories.

    Parameters
    ----------
    mode: Mode
        The mode to use for the palette.
    categories: List[str]
        A list of categories to be rendered.

    Returns
    -------
    Palette
        A dict of categories and their corresponding palette value.
    """

    if not mode in get_args(Mode):
        raise ValueError(f"Unknown mode {mode}.") from DarwinException

    if not isinstance(categories, list) or not categories:
        raise ValueError(f"categories must be a non-empty list. Got {categories}.")

    num_categories: int = len(categories)
    if mode == "index":
        if num_categories > 254:
            raise ValueError("maximum number of classes supported: 254.")
        palette = {c: i for i, c in enumerate(categories)}

    if mode == "grey":
        if num_categories > 254:
            raise ValueError("maximum number of classes supported: 254.")
        elif num_categories == 1:
            raise ValueError("only having the '__background__' class is not allowed. Please add more classes.")

        palette = {c: int(i * 255 / (num_categories - 1)) for i, c in enumerate(categories)}

    if mode == "rgb":
        if num_categories > 360:
            raise ValueError("maximum number of classes supported: 360.")
        palette = {c: i for i, c in enumerate(categories)}

    if not palette:
        raise ValueError(f"Failed to generate a palette.", mode, categories) from DarwinException

    if mode == "rgb":
        # Generate HSV colors for all classes except for BG
        HSV_colors = [(x / num_categories, 0.8, 1.0) for x in range(num_categories - 1)]
        RGB_color_list = list(map(lambda x: [int(e * 255) for e in colorsys.hsv_to_rgb(*x)], HSV_colors))
        # Now we add BG class with [0 0 0] RGB value
        RGB_color_list.insert(0, [0, 0, 0])
        palette_rgb = {c: rgb for c, rgb in zip(categories, RGB_color_list)}
        RGB_colors = [c for e in RGB_color_list for c in e]

    #! Confused, where do these values come from if it's not rgb?

    return palette, RGB_colors, HSV_colors, RGB_color_list, palette_rgb  # TODO: correct return sig


def get_render_mode(annotations: List[dt.AnnotationLike]) -> TypeOfRender:
    """
    Returns the type of render mode for the given annotations.

    Parameters
    ----------
    annotations: List[dt.AnnotationLike]
        A list of annotations to be rendered.

    Returns
    -------
    TypeOfRenderType
        A string reading either "raster" or "polygon".
    """
    non_video_annotations: List[dt.Annotation] = [a for a in annotations if not isinstance(a, dt.VideoAnnotation)]

    list_of_keys: List[str] = reduce(list.__add__, [list(a.data.keys()) for a in non_video_annotations])
    keys: Set[str] = set(list_of_keys)

    is_raster_mask = ("mask" in keys) and ("raster_layer" in keys)
    is_polygon = ("polygon" in keys) or ("complex_polygon" in keys)

    raster_layer_count = len([a for a in keys if a == "raster_layer"])

    if is_raster_mask and is_polygon:
        raise ValueError("Cannot have both raster and polygon annotations in the same file")

    if is_raster_mask and raster_layer_count > 1:
        raise ValueError("Cannot have more than one raster layer in the same file")

    if is_raster_mask:
        return "raster"

    if is_polygon:
        return "polygon"

    raise ValueError("No renderable annotations found in file, found keys: " + ",".join(keys))


def rle_decode(rle: UndecodedRLE) -> DecodedRLE:
    """Decodes a run-length encoded list of integers.

    Args:
        rle (List[int]): A run-length encoded list of integers.

    Returns:
        List[int]: The decoded list of integers.
    """
    if len(rle) % 2 != 0:
        raise ValueError("RLE must be a list of pairs of integers.")

    output: DecodedRLE = reduce(
        list.__add__, [[value] * count for value, count in [(rle[i], rle[i + 1]) for i in range(0, len(rle), 2)]]  # type: ignore
    )  # Non-verbose, but performant way of flattening a list of lists

    return output


def render_polygons(
    mask: Image,
    palette: Palette,
    categories: CategoryList,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,
    height: int,
    width: int,
) -> Tuple[List[Exception], Image, CategoryList]:
    errors: List[Exception] = []

    for a in annotations:
        try:
            if isinstance(a, dt.VideoAnnotation):
                print(f"Skipping video annotation from file {annotation_file.filename}")
                continue

            cat = a.annotation_class.name
            if a.annotation_class.annotation_type == "polygon":
                polygon = a.data["path"]
            elif a.annotation_class.annotation_type == "complex_polygon":
                polygon = a.data["paths"]
            else:
                raise ValueError(f"Unknown annotation type {a.annotation_class.annotation_type}")
            sequence = convert_polygons_to_sequences(polygon, height=height, width=width)
            mask = draw_polygon(mask, sequence, palette[cat])
        except Exception as e:
            errors.append(e)
            continue

    # It's not necessary to return the mask, it's modified in place, but it's more explicit
    return errors, mask, categories


def render_raster(
    mask: Image,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,
    height: int,
    width: int,
) -> Tuple[List[Exception], Image, CategoryList]:
    errors: List[Exception] = []

    mask_annotations: List[dt.AnnotationMask] = []
    raster_layer: Optional[dt.RasterLayer] = None

    categories: CategoryList = []

    for a in annotations:
        if isinstance(a, dt.VideoAnnotation):
            errors.append(f"Skipping video annotation from file {annotation_file.filename}")
            continue

        if m := getattr(a, "mask"):
            new_mask = dt.AnnotationMask(
                id=getattr(m, "id"),
                name=getattr(m, "name"),
                slot_names=getattr(m, "slot_names"),
            )
            new_mask.validate()

            mask_annotations.append(m)

        if rl := getattr(a, "raster_layer"):

            if raster_layer:
                errors.append(ValueError(f"Annotation {a.id} has more than one raster layer"))
                break

            #! Correct the interface below
            new_rl = dt.RasterLayer(
                id=getattr(rl, "id"),
                name=getattr(rl, "name"),
                slot_names=getattr(rl, "slot_names"),
                dense_rle=getattr(rl, "dense_rle"),
            )
            new_rl.validate()
            raster_layer = new_rl

    if not raster_layer:
        errors.append(ValueError(f"Annotation has no raster layer"))
        return errors, mask

    if not (rle := raster_layer.rle):
        errors.append(ValueError(f"Annotation has no RLE data"))
        return errors, mask

    # TODO: Correlate masks with classes, and return for adding to CSV

    rle_decoded = rle_decode(rle)
    mask_array = np.array(rle_decoded).reshape(height, width)

    # TODO: Retrieve a list of palette for the list of categories

    # Colour the image with palette
    mask_array = np.where(mask_array == 1, palette[category], mask_array)

    # Convert to PIL image
    mask = Image.fromarray(mask_array.astype("uint8"), "L")

    # TODO: Correlate masks with classes, and return for adding to CSV

    return errors, mask, classes  # TODO: populate classes


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path, mode: str) -> None:
    masks_dir: Path = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)

    categories: List[str] = extract_categories(annotation_files)
    num_categories = len(categories)

    palette = get_palette(mode=mode, categories=categories)

    for annotation_file in annotation_files:

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

        mask: Image = np.zeros((height, width)).astype(np.uint8)  # type: ignore
        annotations: List[dt.AnnotationLike] = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]

        type = get_render_mode(annotations)

        if type == "raster":
            errors, mask, categories = render_raster(mask, annotations, annotation_file, height, width)

        else:
            categories = extract_categories(annotations)
            palette = get_palette(mode, categories)

            errors, mask = render_polygons(mask, annotations, annotation_file, height, width, palette)

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
