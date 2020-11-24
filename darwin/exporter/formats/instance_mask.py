import os
import shutil
from pathlib import Path
from typing import Generator

from PIL import Image

import darwin.datatypes as dt
from darwin.utils import (
    convert_bounding_box_to_mask,
    convert_ellipse_to_mask,
    convert_polygons_to_mask,
    get_progress_bar,
)


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    masks_dir = output_dir / "masks"
    if masks_dir.exists():
        shutil.rmtree(masks_dir)
    masks_dir.mkdir(parents=True)
    with open(output_dir / "instance_mask_annotations.csv", "w") as f:
        f.write("image_id,mask_id,class_name\n")
        for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
            image_id = os.path.splitext(annotation_file.filename)[0]
            height = annotation_file.image_height
            width = annotation_file.image_width
            for i, annotation in enumerate(annotation_file.annotations):
                cat = annotation.annotation_class.name
                if annotation.annotation_class.annotation_type == "polygon":
                    mask = convert_polygons_to_mask(annotation.data["path"], height=height, width=width, value=255)
                elif annotation.annotation_class.annotation_type == "complex_polygon":
                    mask = convert_polygons_to_mask(annotation.data["paths"], height=height, width=width, value=255)
                elif annotation.annotation_class.annotation_type == "ellipse":
                    mask = convert_ellipse_to_mask(annotation.data, height=height, width=width, value=255)
                elif annotation.annotation_class.annotation_type == "bounding_box":
                    mask = convert_bounding_box_to_mask(annotation.data, height=height, width=width, value=255)
                else:
                    continue
                mask = Image.fromarray(mask)
                mask_id = f"{image_id}_{i:05}"
                outfile = masks_dir / f"{mask_id}.png"
                outfile.parent.mkdir(parents=True, exist_ok=True)
                mask.save(outfile)
                f.write(f"{image_id},{mask_id},{cat}\n")
