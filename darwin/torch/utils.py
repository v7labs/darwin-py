import os
import sys
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
import torch

from darwin.datatypes import ComplexPolygon, Polygon
from upolygon import draw_polygon


def convert_polygon_to_mask(segmentations: List[List[float]], height: int, width: int):
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
    for contour in segmentations:
        contour = [c.tolist() for c in contour]
        mask = torch.zeros((height, width)).numpy().astype(np.uint8)
        masks.append(torch.from_numpy(np.asarray(draw_polygon(mask, contour, 1))))
    return torch.stack(masks)


def convert_polygons_to_sequences(polygons: Union[Polygon, ComplexPolygon]) -> List[np.ndarray]:
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


def detectron2_register_dataset(
    dataset_path: Union[Path, str],
    partition: Optional[str] = None,
    split: Optional[str] = 'default',
    split_type: Optional[str] = "stratified",
    release_name: Optional[str] = None,
    evaluator_type: Optional[str] = None,
):
    """ Registers a local Darwin-formatted dataset in Detectron2

    Parameters
    ----------
    dataset_path: Path, str
        Path to the location of the dataset on the file system
    partition: str
        Selects one of the partitions [train, val, test]
    split
        Selects the split that defines the percetages used (use 'default' to select the default split)
    split_type: str
        Heuristic used to do the split [random, stratified]
    release_name: str
        Version of the dataset
    evaluator_type: str
        Evaluator to be used in the val and test sets
    """
    try:
        from detectron2.data import MetadataCatalog, DatasetCatalog
    except ImportError:
        print("Detectron2 not found.")
        sys.exit(1)
    from darwin.dataset.utils import get_annotations, get_classes

    catalog_name = f"darwin_{os.path.basename(dataset_path)}"
    if partition:
        catalog_name += f"_{partition}"
    classes = get_classes(dataset_path, annotation_type='polygon')
    DatasetCatalog.register(
        catalog_name,
        lambda partition=partition: list(get_annotations(
            dataset_path,
            partition=partition,
            split_type=split_type,
            release_name=release_name,
            annotation_type="polygon",
            annotation_format="coco",
        ))
    )
    MetadataCatalog.get(catalog_name).set(thing_classes=classes)
    if evaluator_type and partition in ['val', 'test']:
        MetadataCatalog.get(catalog_name).set(evaluator_type=evaluator_type)
    return catalog_name
