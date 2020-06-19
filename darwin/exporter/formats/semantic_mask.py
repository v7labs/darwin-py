from pathlib import Path
from typing import Generator, List, Optional

import numpy as np
from PIL import Image
from upolygon import draw_polygon

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar, ispolygon


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    annotation_files = list(annotation_files)
    categories = calculate_categories(annotation_files)
    ignore_idx = 255
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
                mask = convert_polygons_to_mask(a.data["path"], height, width)
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
    print(f"Dataset format saved at {output_dir}")


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
