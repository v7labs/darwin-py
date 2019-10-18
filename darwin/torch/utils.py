from typing import List

import numpy as np
import torch
from PIL import Image
from pycocotools import mask as coco_mask

try:
    import accimage
except ImportError:
    accimage = None

def load_pil_image(path):
    """
    Loads a PIL image and converts it into RGB.

    Input:
        path: path to the image file

    Output:
        PIL Image
    """
    pic = Image.open(path)
    if pic.mode == "RGB":
        pass
    elif pic.mode in ("CMYK", "RGBA"):
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

def convert_polygon_to_sequence(polygon: List):
    """
    Converts a sequence of dictionaries of (x,y) into an array of coordinates.

    Input:
        polygon: list of dictionaries -> [{x: x1, y:y1}, ..., {x: xn, y:yn}]

    Output:
        list of float values -> [x1, y1, x2, y2, ..., xn, yn]
    """
    path = []
    if len(polygon) == 0:
        return path
    elif isinstance(polygon[0], dict):
        for e in polygon:
            path.append(e["x"])
            path.append(e["y"])
        return path
    else:
        return polygon

def polygon_area(x, y):
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))
