import shutil
import uuid
from pathlib import Path
from typing import Generator

import numpy as np
from PIL import Image

import darwin.datatypes as dt
from darwin.utils import convert_polygons_to_mask, get_progress_bar, ispolygon


def generate_instance_id(instance_ids, length=8):
    instance_id = uuid.uuid4().hex[:length]
    while instance_id in instance_ids:
        instance_id = uuid.uuid4().hex[:length]
    return instance_id


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    masks_dir = output_dir / "masks"
    if masks_dir.exists():
        shutil.rmtree(masks_dir)
    masks_dir.mkdir(parents=True)
    instance_ids = set()
    with open(output_dir / "instance_mask_annotations.csv", "w") as f:
        f.write("image_id,mask_id,class_name\n")
        for annotation_file in get_progress_bar(list(annotation_files), "Processing annotations"):
            image_id = annotation_file.path.stem
            height = annotation_file.image_height
            width = annotation_file.image_width
            annotations = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
            for annotation in annotations:
                cat = annotation.annotation_class.name
                instance_id = generate_instance_id(instance_ids)
                instance_ids.add(instance_id)
                mask = convert_polygons_to_mask(annotation.data["path"], height, width) * 255
                mask = Image.fromarray(mask.astype(np.uint8))
                mask_id = f"{image_id}_{instance_id}"
                mask.save(masks_dir / f"{mask_id}.png")
                f.write(f"{image_id},{mask_id},{cat}\n")
        print(f"Dataset format saved at {output_dir}")
