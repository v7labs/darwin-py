import colorsys
import math
import os
from csv import writer as csv_writer
from functools import reduce
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional, Set, Tuple, get_args

import numpy as np

try:
    from numpy.typing import NDArray
except ImportError:
    NDArray = Any  # type:ignore
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
    SATURATION_OF_COLOUR: float = 0.8
    VALUE_OF_COLOUR: float = 1.0
    hsv_colours: dt.MaskTypes.HsvColors = [
        (x / num_categories, SATURATION_OF_COLOUR, VALUE_OF_COLOUR) for x in range(num_categories - 1)
    ]
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

    if not non_video_annotations:
        return "polygon"

    list_of_types: List[str] = [a.annotation_class.annotation_type for a in non_video_annotations]
    types: Set[str] = set(list_of_types)

    is_raster_mask = ("mask" in types) and ("raster_layer" in types)
    is_polygon = ("polygon" in types) or ("complex_polygon" in types)

    raster_layer_count = len([a for a in types if a == "raster_layer"])

    if is_raster_mask and is_polygon:
        raise ValueError("Cannot have both raster and polygon annotations in the same file")

    if is_raster_mask and raster_layer_count > 1:
        raise ValueError("Cannot have more than one raster layer in the same file")

    if is_raster_mask:
        return "raster"

    if is_polygon:
        return "polygon"

    raise ValueError("No renderable annotations found in file, found types: " + ",".join(list_of_types))


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
    for uuid, colour_value in raster_layer.mask_annotation_ids_mapping.items():
        mask: Optional[dt.AnnotationMask] = mask_lookup.get(uuid)

        if mask is None:
            raise ValueError(f"Could not find mask with uuid {uuid} in mask lookup table.")

        if not mask.name in colours:
            colours[mask.name] = colour_value

    return colours  # Returns same item as the outset, technically not needed, but best practice.


def rle_decode(rle: dt.MaskTypes.UndecodedRLE) -> List[int]:
    """Decodes a run-length encoded list of integers.

    Args:
        rle (List[int]): A run-length encoded list of integers.

    Returns:
        List[int]: The decoded list of integers.
    """
    if len(rle) % 2 != 0:
        raise ValueError("RLE must be a list of pairs of integers.")

    output = []
    for i in range(0, len(rle), 2):
        output += [rle[i]] * rle[i + 1]

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
    mask: NDArray,
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
    mask: NDArray
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

    filtered_annotations: List[dt.Annotation] = [a for a in annotations if not isinstance(a, dt.VideoAnnotation)]
    beyond_window = annotations_exceed_window(filtered_annotations, height, width)
    if beyond_window:
        # If the annotations exceed the window, we need to offset the mask to fit them all in.
        # Capture the offsets so we can shift the annotations back to their original positions later
        x_min, x_max, y_min, y_max = get_extents(filtered_annotations, height, width)
        new_height = y_max - y_min
        new_width = x_max - x_min
        mask = np.zeros((new_height, new_width), dtype=np.uint8)
        offset_x, offset_y = -x_min, -y_min

    for a in filtered_annotations:
        try:
            cat = a.annotation_class.name
            if not cat in categories:
                categories.append(cat)

            if a.annotation_class.annotation_type == "polygon":
                polygon = a.data["path"]
            elif a.annotation_class.annotation_type == "complex_polygon":
                polygon = a.data["paths"]
            else:
                raise ValueError(f"Unknown annotation type {a.annotation_class.annotation_type}")

            if beyond_window:
                # Offset the polygon by the minimum x and y values to shift it to new frame of reference
                polygon_off = offset_polygon(polygon, offset_x, offset_y)
                sequence = convert_polygons_to_sequences(polygon_off, height=new_height, width=new_width)
            else:
                sequence = convert_polygons_to_sequences(polygon, height=height, width=width)
            colour_to_draw = categories.index(cat)
            mask = draw_polygon(mask, sequence, colour_to_draw)

            if cat not in colours:
                colours[cat] = colour_to_draw

        except Exception as e:
            errors.append(e)
            continue

    if beyond_window:
        # crop the mask to the original image size and in the correct offset location
        mask = mask[offset_y : offset_y + height, offset_x : offset_x + width]
    # It's not necessary to return the mask, it's modified in place, but it's more explicit
    return errors, mask, categories, colours


def render_raster(
    mask: NDArray,
    colours: dt.MaskTypes.ColoursDict,
    categories: dt.MaskTypes.CategoryList,
    annotations: List[dt.AnnotationLike],
    annotation_file: dt.AnnotationFile,  # Not used, but kept for consistency
    height: int,
    width: int,
) -> dt.MaskTypes.RendererReturn:
    """
    Renders the raster layers in the given annotations onto the given mask.

    Parameters
    ----------
    mask: NDArray
        The mask to render the polygons onto. Not used.  Only returned if no errors occur.
    colours: dt.MaskTypes.ColoursDict
        The colours list. Only returned if no errors occur.
    annotations: List[dt.AnnotationLike]
        A list of annotations to be rendered.
    annotation_file: dt.AnnotationFile
        Not used. Present for interface consistency.
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

        data = a.data

        if a.annotation_class.annotation_type == "mask" and a.id:
            new_mask = dt.AnnotationMask(
                id=a.id,
                name=a.annotation_class.name,
                slot_names=a.slot_names,
            )
            try:
                new_mask.validate()
            except Exception as e:
                errors.append(e)
                continue

            mask_annotations.append(new_mask)

            if not new_mask.id in mask_lookup:
                mask_lookup[new_mask.id] = new_mask

            # Add the category to the list of categories
            if not new_mask.name in categories:
                categories.append(new_mask.name)

        if a.annotation_class.annotation_type == "raster_layer" and (rl := data):
            if raster_layer:
                errors.append(ValueError(f"Annotation {a.id} has more than one raster layer"))
                break

            new_rl = dt.RasterLayer(
                rle=rl["dense_rle"],
                decoded=rle_decode(rl["dense_rle"]),  # type: ignore
                slot_names=a.slot_names,
                mask_annotation_ids_mapping=rl["mask_annotation_ids_mapping"],
                total_pixels=rl["total_pixels"],
            )
            new_rl.validate()
            raster_layer = new_rl

    if not raster_layer:
        errors.append(ValueError(f"Annotation has no raster layer"))
        return errors, mask, categories, colours

    if not mask_annotations:
        errors.append(ValueError(f"Annotation has no masks"))
        return errors, mask, categories, colours

    try:
        colours = colours_in_rle(colours, raster_layer, mask_lookup)
    except Exception as e:
        errors.append(e)

    mask = np.array(raster_layer.decoded, dtype=np.uint8).reshape(height, width)

    return errors, mask, categories, colours


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path, mode: dt.MaskTypes.Mode) -> None:
    masks_dir: Path = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)
    accepted_types = ["polygon", "complex_polygon", "raster_layer", "mask"]
    all_classes_sets: List[Set[dt.AnnotationClass]] = [a.annotation_classes for a in annotation_files]
    if len(all_classes_sets) > 0:
        all_classes: Set[dt.AnnotationClass] = set.union(*all_classes_sets)
        categories: List[str] = ["__background__"] + sorted(
            list(set([c.name for c in all_classes if c.annotation_type in accepted_types])), key=lambda x: x.lower()
        )
        palette = get_palette(mode, categories)
    else:
        categories = ["__background__"]
        palette = dict()

    colours: dt.MaskTypes.ColoursDict = dict()

    for annotation_file in annotation_files:
        image_rel_path = os.path.splitext(annotation_file.full_path)[0].lstrip("/")
        outfile = masks_dir / f"{image_rel_path}.png"
        outfile.parent.mkdir(parents=True, exist_ok=True)

        height = annotation_file.image_height
        width = annotation_file.image_width
        if height is None or width is None:
            raise ValueError(f"Annotation file {annotation_file.filename} references an image with no height or width")

        mask: NDArray = np.zeros((height, width)).astype(np.uint8)
        annotations: List[dt.AnnotationLike] = [
            a for a in annotation_file.annotations if a.annotation_class.annotation_type in accepted_types
        ]

        render_type = get_render_mode(annotations)

        if render_type == "raster":
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
        mask = np.array(mask, dtype=np.uint8)  # Final double check that type is using correct dtype

        if mode == "rgb":
            rgb_colours, palette_rgb = get_rgb_colours(categories)
            image = Image.fromarray(mask, "P")
            image.putpalette(rgb_colours)
            image = image.convert("RGB")
        elif mode == "grey":
            for value, colour in enumerate(palette.values()):
                mask = np.where(mask == value, colour, mask)
            image = Image.fromarray(mask)
        else:
            image = Image.fromarray(mask)
        image.save(outfile)

    with open(output_dir / "class_mapping.csv", "w") as f:
        writer = csv_writer(f)
        writer.writerow(["class_name", "class_color"])

        for class_key in categories:
            if mode == "rgb":
                col = palette_rgb[class_key]
                writer.writerow([class_key, f"{col[0]} {col[1]} {col[2]}"])
            else:
                writer.writerow([class_key, f"{palette[class_key]}"])


def annotations_exceed_window(annotations: List[dt.Annotation], height: int, width: int) -> bool:
    """Check if any annotations exceed the image window

    Args:
        annotations (List[dt.Annotation]): List of annotations
        height (int): height of image
        width (int): width of image

    Returns:
        bool: True if any annotation exceeds window, false otherwise
    """
    for item in annotations:
        if "bounding_box" not in item.data:
            continue
        bbox = item.data["bounding_box"]
        if bbox["x"] < 0:
            return True
        if bbox["y"] < 0:
            return True
        if bbox["x"] + bbox["w"] > width:
            return True
        if bbox["y"] + bbox["h"] > height:
            return True
    return False


def get_extents(annotations: List[dt.Annotation], height: int = 0, width: int = 0) -> Tuple[int, int, int, int]:
    """Create a bounding box around all annotations in discrete pixel space

    Args:
        annotations (List[dt.Annotation]): List of annotations
        height (int): Height to start with
        width (int): Width to start with

    Returns:
        Tuple[int, int, int, int]: x_min, x_max, y_min, y_max
    """
    x_min = y_min = 0
    x_max, y_max = width, height
    for item in annotations:
        if "bounding_box" not in item.data:
            continue
        bbox = item.data["bounding_box"]
        x_min = min(x_min, bbox["x"])
        x_max = max(x_max, bbox["x"] + bbox["w"])
        y_min = min(y_min, bbox["y"])
        y_max = max(y_max, bbox["y"] + bbox["h"])
    return math.floor(x_min), math.ceil(x_max), math.floor(y_min), math.ceil(y_max)


def offset_polygon(polygon: List, offset_x: int, offset_y: int) -> List:
    """Offsets a polygon by a given amount

    Args:
        polygon (List): List of coordinates
        offset_x (int): x offset value
        offset_y (int): y offset value

    Returns:
        List: polygon with offset applied
    """
    if isinstance(polygon[0], list):
        return offset_complex_polygon(polygon, offset_x, offset_y)
    else:
        return offset_simple_polygon(polygon, offset_x, offset_y)


def offset_complex_polygon(polygons: List, offset_x: int, offset_y: int) -> List:
    new_polygons = []
    for polygon in polygons:
        new_polygons.append(offset_simple_polygon(polygon, offset_x, offset_y))
    return new_polygons


def offset_simple_polygon(polygon: List, offset_x: int, offset_y: int) -> List:
    new_polygon = []
    for point in polygon:
        new_polygon.append({"x": point["x"] + offset_x, "y": point["y"] + offset_y})
    return new_polygon
