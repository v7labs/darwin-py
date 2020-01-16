import itertools
import json
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
from PIL import Image

from pycocotools import mask as coco_mask
from darwin.dataset.utils import get_classes

try:
    from detectron2.structures import BoxMode
except ImportError:
    BoxMode = None

try:
    import accimage
except ImportError:
    accimage = None


def load_pil_image(path: Path):
    """
    Loads a PIL image and converts it into RGB.

    Parameters
    ----------
    path: Path
        Path to the image file

    Returns
    -------
    PIL Image
        Values between 0 and 255
    """
    pic = Image.open(path)
    if pic.mode == "RGB":
        pass
    elif pic.mode in ("CMYK", "RGBA", "P"):
        pic = pic.convert("RGB")
    elif pic.mode == "I":
        img = (np.divide(np.array(pic, np.int32), 2 ** 16 - 1) * 255).astype(np.uint8)
        pic = Image.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "I;16":
        img = (np.divide(np.array(pic, np.int16), 2 ** 8 - 1) * 255).astype(np.uint8)
        pic = Image.fromarray(np.stack((img, img, img), axis=2))
    elif pic.mode == "L":
        img = np.array(pic).astype(np.uint8)
        pic = Image.fromarray(np.stack((img, img, img), axis=2))
    else:
        raise TypeError(f"unsupported image type {pic.mode}")
    return pic


def _is_pil_image(img):
    if accimage is not None:
        return isinstance(img, (Image.Image, accimage.Image))
    else:
        return isinstance(img, Image.Image)


def convert_polygon_to_mask(segmentations: List[float], height: int, width: int):
    """
    Converts a polygon represented as a sequence of coordinates into a mask.

    Input:
        segmentations: list of float values -> [x1, y1, x2, y2, ..., xn, yn]
        height: image's height
        width: image's width

    Output:
        torch.tensor
    """
    masks = []
    for polygons in segmentations:
        rles = coco_mask.frPyObjects(polygons, height, width)
        mask = coco_mask.decode(rles)
        if len(mask.shape) < 3:
            mask = mask[..., None]
        mask = torch.as_tensor(mask, dtype=torch.uint8)
        mask = mask.any(dim=2)
        masks.append(mask)
    if masks:
        masks = torch.stack(masks, dim=0)
    else:
        masks = torch.zeros((0, height, width), dtype=torch.uint8)
    return masks


def convert_polygons_to_sequences(polygons: List) -> List[np.ndarray]:
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
    # If there is a single polygon composing the instance the format is going to be
    # polygons = [{x: x1, y:y1}, ..., {x: xn, y:yn}]
    if isinstance(polygons[0], dict):
        path = []
        for point in polygons:
            path.append(point["x"])
            path.append(point["y"])
        return [np.array(path)]  # List type is used for backward compatibility
    # If there are multiple polygons composing the instance the format is going to be
    # polygons =  [[{x: x1, y:y1}, ..., {x: xn, y:yn}], ..., [{x: x1, y:y1}, ..., {x: xn, y:yn}]]
    if isinstance(polygons[0], list) and isinstance(polygons[0][0], dict):
        sequences = []
        for polygon in polygons:
            path = []
            for point in polygon:
                path.append(point["x"])
                path.append(point["y"])
            sequences.append(np.array(path))
        return sequences
    raise ValueError("Unknown input format")


def polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def get_annotations(
    dataset,
    partition: str,
    split: Optional[str] = 'split',
    split_type: Optional[str] = 'stratified',
    annotation_type: Optional[str] = 'polygon'
):
    """
    Returns all the annotations of a given dataset and split in a single dictionary

    Parameters
    ----------
    dataset
        Path to the location of the dataset on the file system
    partition
        Selects one of the partitions [train, val, test]
    split
        Selects the split that defines the percetages used (use 'split' to select the default split
    split_type
        Heuristic used to do the split [random, stratified]
    annotation_type
        The type of annotation classes [tag, polygon]

    Returns
    -------
    dict
        Dictionary containing all the annotations of the dataset
    """
    assert dataset is not None
    if isinstance(dataset, Path) or isinstance(dataset, str):
        dataset_path = Path(dataset)
    else:
        dataset_path = dataset.local_path

    if partition not in ['train', 'val', 'test']:
        raise ValueError("partition should be either 'train', 'val', or 'test'")
    if split_type not in ['random', 'stratified']:
        raise ValueError("split_type should be either 'random' or 'stratified'")
    if annotation_type not in ['tag', 'polygon']:
        raise ValueError("annotation_type should be either 'tag' or 'polygon'")

    # Get the list of classes
    classes = get_classes(dataset, annotation_type=annotation_type, remove_background=True)
    # Get the split
    if split_type == 'random':
        split_file = f"{split_type}_{partition}.txt"
    elif split_type == 'stratified':
        split_file = f"{split_type}_{annotation_type}_{partition}.txt"
    split_path = dataset_path / "lists" / split / split_file
    stems = (e.strip() for e in split_path.open())
    extensions = [".jpg", ".jpeg", ".png"]
    images_path = []
    annotations_path = []

    # Find all the annotations and their corresponding images
    for stem in stems:
        annotation_path = dataset_path / f"annotations/{stem}.json"
        images = [
            image for image in dataset_path.glob(f"images/{stem}.*") if image.suffix.lower() in extensions
        ]
        if len(images) < 1:
            raise ValueError(
                f"Annotation ({annotation_path}) does" f" not have a corresponding image"
            )
        if len(images) > 1:
            raise ValueError(
                f"Image ({stem}) is present with multiple extensions." f" This is forbidden."
            )
        assert len(images) == 1
        image_path = images[0]
        images_path.append(image_path)
        annotations_path.append(annotation_path)

    if len(images_path) == 0:
        raise ValueError(f"Could not find any {extensions} file" f" in {dataset_path / 'images'}")

    assert len(images_path) == len(annotations_path)

    # Load and re-format all the annotations
    dataset_dicts = []
    for im_path, annot_path in zip(images_path, annotations_path):
        record = {}

        with annot_path.open() as f:
            data = json.load(f)

        height, width = data["image"]["height"], data["image"]["width"]
        annotations = data["annotations"]

        filename = im_path
        record["file_name"] = str(filename)
        record["height"] = height
        record["width"] = width

        objs = []
        for obj in annotations:
            px, py = [], []
            if "polygon" not in obj:
                continue
            for point in obj["polygon"]["path"]:
                px.append(point["x"])
                py.append(point["y"])
            poly = [(x, y) for x, y in zip(px, py)]
            if len(poly) < 3:  # Discard polyhons with less than 3 points
                continue
            poly = list(itertools.chain.from_iterable(poly))

            category_id = classes.index(obj["name"])

            if BoxMode is not None:
                box_mode = BoxMode.XYXY_ABS
            else:
                box_mode = 0

            obj = {
                "bbox": [np.min(px), np.min(py), np.max(px), np.max(py)],
                "bbox_mode": box_mode,
                "segmentation": [poly],
                "category_id": category_id,
                "iscrowd": 0,
            }
            objs.append(obj)
        record["annotations"] = objs
        dataset_dicts.append(record)
    return dataset_dicts
