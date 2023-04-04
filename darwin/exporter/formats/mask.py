import colorsys
import os
from csv import writer as csv_writer
from functools import reduce
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Set, Tuple, get_args

import numpy as np
from PIL import Image
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.exceptions import DarwinException
from darwin.utils import convert_polygons_to_sequences, ispolygon


def get_palette(mode: dt.MaskTypes.Mode, categories: List[str]) -> dt.MaskTypes.Palette:
    """
    Returns a palette for the given mode and categories.

    Parameters
    ----------
    mode: dt.MaskTypes.Mode
        The mode to use for the palette.
    categories: List[str]
        A list of categories to be rendered.

    Returns
    -------
    dt.MaskTypes.Palette
        A dict of categories and their corresponding palette value.
    """

    if not mode in get_args(dt.MaskTypes.Mode):
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

    return palette


def get_rgb_colours(categories: dt.MaskTypes.CategoryList) -> Tuple[dt.MaskTypes.RgbColors, dt.MaskTypes.RgbPalette]:
    """
    Returns a list of RGB colours and a dict of categories and their corresponding RGB palette value.

    Parameters
    ----------
    categories: dt.MaskTypes.CategoryList
        A list of categories to be rendered.

    Returns
    -------
    dt.MaskTypes.RgbColors
        A list of RGB colours for each category.
    dt.MaskTypes.RgbPalette
        A dict of categories and their corresponding RGB palette value.
    """
    num_categories: int = len(categories)

    # Generate HSV colours for all classes except for BG
    hsv_colours: dt.MaskTypes.HsvColors = [(x / num_categories, 0.8, 1.0) for x in range(num_categories - 1)]
    rgb_colour_list: dt.MaskTypes.RgbColorList = list(
        map(lambda x: [int(e * 255) for e in colorsys.hsv_to_rgb(*x)], hsv_colours)
    )
    # Now we add BG class with [0 0 0] RGB value
    rgb_colour_list.insert(0, [0, 0, 0])
    palette_rgb: dt.MaskTypes.RgbPalette = {c: rgb for c, rgb in zip(categories, rgb_colour_list)}
    rgb_colours: dt.MaskTypes.RgbColors = [c for e in rgb_colour_list for c in e]

    return rgb_colours, palette_rgb


def get_render_mode(annotations: List[dt.AnnotationLike]) -> dt.MaskTypes.TypeOfRender:
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


def colours_in_rle(
    colours: dt.MaskTypes.ColoursDict,
    raster_layer: dt.RasterLayer,
    mask_lookup: Dict[str, dt.AnnotationMask],
) -> dt.MaskTypes.ColoursDict:
    """
    Returns a dictionary of colours for each mask in the given RLE.

    Parameters
    ----------
    colours: dt.MaskTypes.ColoursDict
        A dictionary of colours for each mask in the given RLE.
    mask_annotations: List[dt.AnnotationMask]
        A list of masks to get the colours for.
    mask_lookup: Set[str, dt.AnnotationMask]
        A lookup table for the masks.

    Returns
    -------
    dt.MaskTypes.ColoursDict
        A dictionary of colours for each mask in the given RLE.
    """
    for uuid, colour_value in raster_layer.mask_mappings.items():
        mask: Optional[dt.AnnotationMask] = mask_lookup.get(uuid)

        if mask is None:
            raise ValueError(f"Could not find mask with uuid {uuid} in mask lookup table.")

        if not mask.name in colours:
            colours[mask.name] = colour_value

    return colours  # Returns same item as the outset, technically not needed, but best practice.


def rle_decode(rle: dt.MaskTypes.UndecodedRLE) -> dt.MaskTypes.DecodedRLE:
    """Decodes a run-length encoded list of integers.

    Args:
        rle (List[int]): A run-length encoded list of integers.

    Returns:
        List[int]: The decoded list of integers.
    """
    if len(rle) % 2 != 0:
        raise ValueError("RLE must be a list of pairs of integers.")

    output: dt.MaskTypes.DecodedRLE = reduce(
        list.__add__, [[value] * count for value, count in [(rle[i], rle[i + 1]) for i in range(0, len(rle), 2)]]  # type: ignore
    )  # Non-verbose, but performant way of flattening a list of lists

    return output


def get_or_generate_colour(cat_name: str, colours: dt.MaskTypes.ColoursDict) -> int:
    """
    Returns the colour for the given category name, or generates a new one if it doesn't exist.

    Parameters
    ----------
    cat_name: str
        The name of the category.
    colours: dt.MaskTypes.ColoursDict
        A dictionary of category names and their corresponding colours.

    Returns
    -------
    int - the integer for the colour name.  These will later be reassigned to a wider spread across the colour spectrum.
    """
    if not cat_name in colours:
        colours[cat_name] = len(colours) + 1

    return colours[cat_name]


def render_polygons(
    mask: Image.Image,
    colours: dt.MaskTypes.ColoursDict,
    categories: dt.MaskTypes.CategoryList,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,
    height: int,
    width: int,
) -> dt.MaskTypes.RendererReturn:
    """
    Renders the polygons in the given annotations onto the given mask.

    Parameters
    ----------
    mask: Image.Image
        The mask to render the polygons onto.
    colours: dt.MaskTypes.ColoursDict
        A dictionary of category names and their corresponding colours.
    categories: dt.MaskTypes.CategoryList
        A list of category names.
    annotations: List[dt.AnnotationLike]
        A list of annotations to be rendered.
    annotation_file: dt.AnnotationFile
        The annotation file that the annotations belong to.
    height: int
        The height of the image.
    width: int
        The width of the image.

    Returns
    -------
    Tuple[List[Exception], Image, dt.MaskTypes.CategoryList, dt.MaskTypes.ColoursDict]
    """

    errors: List[Exception] = []

    for a in annotations:
        try:
            if isinstance(a, dt.VideoAnnotation):
                print(f"Skipping video annotation from file {annotation_file.filename}")
                continue

            cat = a.annotation_class.name
            if not cat in categories:
                categories.append(cat)

            if a.annotation_class.annotation_type == "polygon":
                polygon = a.data["path"]
            elif a.annotation_class.annotation_type == "complex_polygon":
                polygon = a.data["paths"]
            else:
                raise ValueError(f"Unknown annotation type {a.annotation_class.annotation_type}")
            sequence = convert_polygons_to_sequences(polygon, height=height, width=width)

            colour_to_draw = get_or_generate_colour(cat, colours)
            mask = draw_polygon(mask, sequence, colour_to_draw)
        except Exception as e:
            errors.append(e)
            continue

    # It's not necessary to return the mask, it's modified in place, but it's more explicit
    return errors, mask, categories, colours


def render_raster(
    mask: Image.Image,
    colours: dt.MaskTypes.ColoursDict,
    categories: dt.MaskTypes.CategoryList,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,
    height: int,
    width: int,
) -> dt.MaskTypes.RendererReturn:
    """
    Renders the raster layers in the given annotations onto the given mask.

    Parameters
    ----------
    mask: Image
        The mask to render the polygons onto.
    annotations: List[dt.AnnotationLike]
        A list of annotations to be rendered.
    annotation_file: dt.AnnotationFile
        The annotation file that the annotations belong to.
    height: int
        The height of the image.
    width: int
        The width of the image.

    Returns
    -------
    Tuple[List[Exception], Image, dt.MaskTypes.CategoryList, dt.MaskTypes.ColoursDict]
    """
    errors: List[Exception] = []

    mask_annotations: List[dt.AnnotationMask] = []
    raster_layer: Optional[dt.RasterLayer] = None

    mask_lookup: Dict[str, dt.AnnotationMask] = dict()

    for a in annotations:
        if isinstance(a, dt.VideoAnnotation):
            continue

        if m := getattr(a, "mask"):
            new_mask = dt.AnnotationMask(
                id=getattr(m, "id"),
                name=getattr(m, "name"),
                slot_names=getattr(m, "slot_names"),
            )
            new_mask.validate()
            mask_annotations.append(m)

            if not new_mask.id in mask_lookup:
                mask_lookup[new_mask.id] = new_mask

            # Add the category to the list of categories
            if not getattr(m, "name") in categories:
                categories.append(getattr(m, "name"))

        if rl := getattr(a, "raster_layer"):

            if raster_layer:
                errors.append(ValueError(f"Annotation {a.id} has more than one raster layer"))
                break

            new_rl = dt.RasterLayer(
                rle=getattr(rl, "dense_rle"),
                decoded=rle_decode(getattr(rl, "dense_rle")),  # type: ignore
                slot_names=getattr(rl, "slot_names"),
                mask_mappings=getattr(rl, "mask_mappings"),
                total_pixels=getattr(rl, "total_pixels"),
            )
            new_rl.validate()
            raster_layer = new_rl

    if not raster_layer:
        errors.append(ValueError(f"Annotation has no raster layer"))
        return errors, mask, categories, colours

    if not mask_annotations:
        errors.append(ValueError(f"Annotation has no masks"))
        return errors, mask, categories, colours

    if not (rle := raster_layer.rle):
        errors.append(ValueError(f"Annotation has no RLE data"))
        return errors, mask, categories, colours

    try:
        colours = colours_in_rle(colours, raster_layer, mask_lookup)
    except Exception as e:
        errors.append(e)

    rle_decoded = rle_decode(rle)
    mask_array = np.array(rle_decoded).reshape(height, width)

    # draw mask_array onto mask
    mask = Image.fromarray(mask_array)  #! Double check this actually works.

    return errors, mask, categories, colours


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path, mode: dt.MaskTypes.Mode) -> None:
    masks_dir: Path = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)

    categories: List[str] = []
    colours: dt.MaskTypes.ColoursDict = dict()

    for annotation_file in annotation_files:

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
            # Add categories to list
            errors, mask, categories, colours = render_raster(
                mask, colours, categories, annotations, annotation_file, height, width
            )

        else:
            #  Add categories to list
            errors, mask, categories, colours = render_polygons(
                mask, colours, categories, annotations, annotation_file, height, width
            )

        if errors:
            print(f"Errors rendering {annotation_file.filename}:")
            for e in errors:
                print(e)

            raise DarwinException.from_multiple_exceptions(errors)

        # Map to palette
        palette = get_palette(mode, categories)
        if mode == "rgb":
            rgb_colours, palette_rgb = get_rgb_colours(categories)
            mask = Image.fromarray(mask, "P")
            mask.putpalette(rgb_colours)
        else:
            mask = Image.fromarray(mask)
        mask.save(outfile)

    with open(output_dir / "class_mapping.csv", "w") as f:
        writer = csv_writer(f)
        writer.writerow(["class_name", "class_color"])

        for c in categories:
            if mode == "rgb":
                writer.writerow([c, f"{palette_rgb[c][0]} {palette_rgb[c][1]} {palette_rgb[c][2]}"])
            else:
                writer.writerow([c, f"{palette[c]}"])
