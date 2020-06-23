from pathlib import Path
from typing import Generator, List

import numpy as np
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar, ispolygon


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path, mode: str = "grayscale"):
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)

    categories = calculate_categories(annotation_files)
    if mode == "index":
        palette = [i for i in range(len(categories))]
        palette[-1] = 255
    elif mode == "grayscale":
        palette = [int(i * 255 / (len(categories)-1)) for i in range(len(categories))]
    elif mode == "rgb":
        raise NotImplementedError
    ignore_value = palette[-1]

    for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
        outfile = masks_dir / f"{annotation_file.path.stem}.png"
        height = annotation_file.image_height
        width = annotation_file.image_width
        annotations = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
        if annotations:
            # compute a mask per category
            mask_per_category = {}
            for a in annotations:
                cat = a.annotation_class.name
                if a.annotation_class.annotation_type == "polygon":
                    polygon = a.data["path"]
                elif a.annotation_class.annotation_type == "complex_polygon":
                    polygon = a.data["paths"]
                else:
                    continue
                mask = convert_polygons_to_mask(polygon, height, width)
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
                    cats.append(palette[cid])
            masks = np.stack(masks, axis=2)
            cats = np.array(cats)
            mask = np.max(masks * cats[None, None, :], axis=2)
            # discard overlapping instances
            mask[np.sum(masks, axis=2) > 1] = ignore_value
            mask = Image.fromarray(mask.astype(np.uint8))
            mask.save(outfile)

    with open(output_dir / "class_mapping.csv", "w") as f:
        f.write(f"class_idx,class_name\n")
        for idx, c in zip(palette, categories):
            f.write(f"{idx},{c}\n")


def calculate_categories(annotation_files: List[dt.AnnotationFile]):
    categories = set()
    for annotation_file in annotation_files:
        for annotation_class in annotation_file.annotation_classes:
            if ispolygon(annotation_class):
                categories.add(annotation_class.name)
    categories = list(categories)
    categories.sort()
    categories.insert(0, "__background__")
    categories.append("__ignore__")
    return categories
