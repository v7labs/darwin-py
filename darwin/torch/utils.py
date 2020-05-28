from typing import List

import numpy as np
import torch

try:
    from pycocotools import mask as coco_mask
except ImportError:
    coco_mask = None


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
    if coco_mask is None:
        raise ImportError("failed to import pycocotools")
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
