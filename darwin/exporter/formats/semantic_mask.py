from pathlib import Path
from typing import Generator, List, Optional
from upolygon import draw_polygon
from PIL import Image

import numpy as np

import darwin.datatypes as dt


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)
    categories = calculate_categories(annotation_files)
    ignore_idx = 255
    for annotation_file in annotation_files:
        outfile = masks_dir / (annotation_file.path.stem + '.png')
        if outfile.exists():
            continue
        height = annotation_file.image_height
        width = annotation_file.image_width
        annotations = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
        if annotations:
            # compute a mask per category
            mask_per_category = {}
            for a in annotations:
                cat = a.annotation_class.name
                sequence = convert_polygons_to_sequences(a.data["path"], height, width)
                mask = convert_polygons_to_mask(sequence, height, width)
                if cat in mask_per_category:
                    mask_per_category[cat] = np.stack((mask_per_category[cat], mask), axis=-1).max(axis=2)
                else:
                    mask_per_category[cat] = mask
            # merge all category masks into a single segmentation map
            # with its corresponding categories
            masks = []
            cats = []
            for cid, c in enumerate(categories):
                if c in mask_per_category:
                    masks.append(mask_per_category[c])
                    cats.append(cid)
            masks = np.stack(masks, axis=2)
            cats = np.array(cats)
            mask = np.max(masks * cats[None, None, :], axis=2)
            # discard overlapping instances
            mask[np.sum(masks, axis=2) > 1] = ignore_idx
            mask = Image.fromarray(mask.astype(np.uint8))
            mask.save(outfile)

    with open(output_dir / "class_mapping.csv", "w") as f:
        f.write(f"class_idx,class_name\n")
        for idx, c in enumerate(categories):
            f.write(f"{idx},{c}\n")
        f.write(f"{ignore_idx},__ignore__")


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


def convert_polygons_to_sequences(polygons: List, height: Optional[int] = None, width: Optional[int] = None) -> List[np.ndarray]:
    """
    Converts a list of polygons, encoded as a list of dictionaries of into a list of nd.arrays
    of coordinates.

    Parameters
    ----------
    polygons: list
        List of coordinates in the format [{x: x1, y:y1}, ..., {x: xn, y:yn}] or a list of them
        as  [[{x: x1, y:y1}, ..., {x: xn, y:yn}], ..., [{x: x1, y:y1}, ..., {x: xn, y:yn}]].

    Returns
    -------
    sequences: list[ndarray[float]]
        List of arrays of coordinates in the format [[x1, y1, x2, y2, ..., xn, yn], ...,
        [x1, y1, x2, y2, ..., xn, yn]]
    """
    if not polygons:
        raise ValueError("No polygons provided")

    # If there is a single polygon composing the instance then this is
    # transformed to polygons = [[{x: x1, y:y1}, ..., {x: xn, y:yn}]]
    if isinstance(polygons[0], dict):
        polygons = [polygons]

    if not isinstance(polygons[0], list) or not isinstance(polygons[0][0], dict):
        raise ValueError("Unknown input format")

    sequences = []
    for polygon in polygons:
        path = []
        for point in polygon:
            # Clip coordinates to the image size
            x = max(min(point["x"], width - 1) if width else point["x"], 0)
            y = max(min(point["y"], height - 1) if height else point["y"], 0)
            path.append(round(x))
            path.append(round(y))
        sequences.append(path)
    return sequences


def convert_polygons_to_mask(polygons, height, width):
    mask = np.zeros((height, width)).astype(np.uint8)
    draw_polygon(mask, polygons, 1)
    return mask


def ispolygon(annotation):
    return annotation.annotation_type in ["polygon", "complex_polygon"]
