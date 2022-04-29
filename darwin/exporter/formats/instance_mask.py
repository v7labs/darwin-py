import os
import shutil
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar, ispolygon


def export(annotation_files: Iterable[dt.AnnotationFile], output_dir: Path) -> None:
    """
    Exports the given ``AnnotationFile``\\s into instance masks format inside of the given
    ``output_dir``. Deletes everything within ``output_dir/masks`` before writting to it.

    Parameters
    ----------
    annotation_files : Iterable[dt.AnnotationFile]
        The ``AnnotationFile``\\s to be exported.
    output_dir : Path
        The folder where the new instance mask files will be.
    """
    masks_dir = output_dir / "masks"
    if masks_dir.exists():
        shutil.rmtree(masks_dir)
    masks_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "instance_mask_annotations.csv", "w") as f:
        f.write("image_id,mask_id,class_name\n")
        for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
            image_id = os.path.splitext(annotation_file.filename)[0]
            height = annotation_file.image_height
            width = annotation_file.image_width
            annotations = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
            for i, annotation in enumerate(annotations):
                cat = annotation.annotation_class.name
                if annotation.annotation_class.annotation_type == "polygon":
                    polygon = annotation.data["path"]
                elif annotation.annotation_class.annotation_type == "complex_polygon":
                    polygon = annotation.data["paths"]
                else:
                    continue
                mask = convert_polygons_to_mask(polygon, height=height, width=width, value=255)
                mask = Image.fromarray(mask.astype(np.uint8))
                mask_id = f"{image_id}_{i:05}"
                outfile = masks_dir / f"{mask_id}.png"
                outfile.parent.mkdir(parents=True, exist_ok=True)
                mask.save(outfile)
                f.write(f"{image_id},{mask_id},{cat}\n")
