from typing import List

import numpy as np
import torch
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


def polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
