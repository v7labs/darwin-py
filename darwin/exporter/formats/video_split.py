import shutil
from pathlib import Path
from typing import Generator

import numpy as np
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar, ispolygon


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    masks_dir = output_dir / "masks"
    if masks_dir.exists():
        shutil.rmtree(masks_dir)
    masks_dir.mkdir(parents=True)
    with open(output_dir / "instance_mask_annotations.csv", "w") as f:
        f.write("image_id,mask_id,class_name\n")
        for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
            for i, annotation_frame in enumerate(annotation_file):
                image_id = f"{annotation_frame.path.stem}_{i:07}"
                height = annotation_frame.image_height
                width = annotation_frame.image_width
                annotations = annotation_frame.annotations
                import pdb; pdb.set_trace()  # XXX BREAKPOINT
                a=1
