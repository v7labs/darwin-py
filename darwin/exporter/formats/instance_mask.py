import uuid
from pathlib import Path
from typing import Generator, List, Optional

import numpy as np
from PIL import Image
from tqdm import tqdm

import darwin.datatypes as dt
from upolygon import draw_polygon


def generate_instance_id(instance_ids, length=8):
    instance_id = uuid.uuid4().hex[:length]
    while instance_id in instance_ids:
        instance_id = uuid.uuid4().hex[:length]
    return instance_id


def export(annotation_files: Generator[dt.AnnotationFile, None, None], output_dir: Path):
    masks_dir = output_dir / "masks"
    masks_dir.mkdir(exist_ok=True, parents=True)
    instance_ids = set()
    with open(output_dir / "instance_mask_annotations.csv", "w") as f:
        f.write("image_id,mask_id,class_name\n")
        pbar = tqdm(list(annotation_files))
        pbar.set_description(desc="Processing annotations", refresh=True)
        for annotation_file in pbar:
            image_id = annotation_file.path.stem
            height = annotation_file.image_height
            width = annotation_file.image_width
            annotations = [a for a in annotation_file.annotations if ispolygon(a.annotation_class)]
            for annotation in annotations:
                cat = annotation.annotation_class.name
                instance_id = generate_instance_id(instance_ids)
                instance_ids.add(instance_id)
                sequence = convert_polygons_to_sequences(annotation.data["path"], height, width)
                mask = convert_polygons_to_mask(sequence, height, width) * 255
                mask = Image.fromarray(mask.astype(np.uint8))
                mask_id = f"{image_id}_{instance_id}"
                mask.save(masks_dir / f"{mask_id}.png")
                f.write(f"{image_id},{mask_id},{cat}\n")
        print(f"Dataset format saved at {output_dir}")


def convert_polygons_to_sequences(
    polygons: List, height: Optional[int] = None, width: Optional[int] = None
) -> List[np.ndarray]:
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
