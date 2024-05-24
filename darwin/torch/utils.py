import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import numpy as np
import torch
from numpy.typing import ArrayLike
from upolygon import draw_polygon

from darwin.cli_functions import _error, _load_client
from darwin.dataset.identifier import DatasetIdentifier
from darwin.datatypes import Segment


def flatten_masks_by_category(masks: torch.Tensor, cats: List[int]) -> torch.Tensor:
    """
    Takes a list of masks and flattens into a single mask output with category id's overlaid into one tensor.
    Overlapping sections of masks are replaced with the top most annotation in that position
    Parameters
    ----------
    masks : torch.Tensor
        lists of masks with shape [x, image_height, image_width] where x is the number of categories
    cats : List[int]
        int list of category id's with len(x)
    Returns
    -------
    torch.Tensor
        Flattened mask of category id's
    """
    assert isinstance(masks, torch.Tensor)
    assert isinstance(cats, List)
    assert masks.shape[0] == len(cats)
    order_of_polygons = list(range(1, len(cats) + 1))
    polygon_mapping = {order: cat for cat, order in zip(cats, order_of_polygons)}
    BACKGROUND: int = 0
    polygon_mapping[BACKGROUND] = 0
    # Uses matrix multiplication here with `masks` being a binary array of same dimensions as image
    # and polygon orders being overlaid onto the relevant mask
    order_tensor = torch.as_tensor(order_of_polygons, dtype=masks.dtype)
    flattened, _ = (masks * order_tensor[:, None, None]).max(dim=0)
    # The mask is now flattened in order of the polygons but needs to be converted back to the categories
    # vectorize the dictionary to return the original category id's
    mapped = np.vectorize(polygon_mapping.__getitem__)(flattened)
    return torch.as_tensor(mapped, dtype=masks.dtype)


def convert_segmentation_to_mask(
    segmentations: List[Segment], height: int, width: int
) -> torch.Tensor:
    """
    Converts a polygon represented as a sequence of coordinates into a mask.

    Parameters
    ----------
    segmentations : List[Segment]
        List of float values -> ``[[x11, y11, x12, y12], ..., [xn1, yn1, xn2, yn2]]``.
    height : int
        Image's height.
    width : int
        Image's width.

    Returns
    -------
    torch.tensor
        A ``Tensor`` representing a segmentation mask.
    """
    if not segmentations:
        return torch.zeros((0, height, width), dtype=torch.uint8)

    masks = []
    for contour in segmentations:
        mask = torch.zeros((height, width)).numpy().astype(np.uint8)
        masks.append(torch.from_numpy(np.asarray(draw_polygon(mask, contour, 1))))
    return torch.stack(masks)


def polygon_area(x: ArrayLike, y: ArrayLike) -> float:
    """
    Returns the area of the input polygon, represented by two numpy arrays for x and y coordinates.

    Parameters
    ----------
    x : np.ndarray
        Numpy array for x coordinates.
    y : np.ndarray
        Numpy array for y coordinates.

    Returns
    -------
    float
        The area of the polygon.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def collate_fn(batch: Iterable[Tuple]) -> Tuple:
    """
    Aggregates the given ``Iterable`` (usually a ``List``) of tuples into a ``Tuple`` of Lists.

    Parameters
    ----------
    batch : Iterable[Tuple]
        Batch to collate.

    Returns
    -------
    Tuple
        The ``Iterable`` of Tupled aggregated into a ``Tuple``.
    """
    return tuple(zip(*batch))


def detectron2_register_dataset(
    dataset: str,
    release_name: Optional[str] = "latest",
    partition: Optional[str] = None,
    split: Optional[str] = "default",
    split_type: Optional[str] = "stratified",
    evaluator_type: Optional[str] = None,
) -> str:
    """
    Registers a local Darwin-formatted dataset in Detectron2.

    Parameters
    ----------
    dataset : str
        Dataset slug.
    release_name : Optional[str], default: "latest"
        Version of the dataset.
    partition : Optional[str], default: None
        Selects one of the partitions ``["train", "val", "test"]``.
    split : Optional[str], default: "default"
        Selects the split that defines the percentages used.
    split_type : Optional[str], default: "stratified"
        Heuristic used to do the split ``["random", "stratified"]``.
    evaluator_type : Optional[str], default: None
        Evaluator to be used in the val and test sets.

    Returns
    -------
    str
        The name of the registered dataset in the format of ``{dataset-name}_{partition}``.
    """
    try:
        from detectron2.data import DatasetCatalog, MetadataCatalog
    except ImportError:
        print("Detectron2 not found.")
        sys.exit(1)
    from darwin.dataset.utils import get_annotations, get_classes

    dataset_path: Optional[Path] = None
    if os.path.isdir(dataset):
        dataset_path = Path(dataset)
    else:
        identifier = DatasetIdentifier.parse(dataset)
        if identifier.version:
            release_name = identifier.version

        client = _load_client(offline=True)
        dataset_path = None
        for path in client.list_local_datasets(team_slug=identifier.team_slug):
            if identifier.dataset_slug == path.name:
                dataset_path = path

        if not dataset_path:
            _error(
                f"Dataset '{identifier.dataset_slug}' does not exist locally. "
                f"Use 'darwin dataset remote' to see all the available datasets, "
                f"and 'darwin dataset pull' to pull them."
            )

    catalog_name = f"darwin_{dataset_path.name}"
    if partition:
        catalog_name += f"_{partition}"

    classes = get_classes(
        dataset_path=dataset_path, release_name=release_name, annotation_type="polygon"
    )

    DatasetCatalog.register(
        catalog_name,
        lambda partition=partition: list(
            get_annotations(
                dataset_path,
                partition=partition,
                split=split,
                split_type=split_type,
                release_name=release_name,
                annotation_type="polygon",
                annotation_format="coco",
                ignore_inconsistent_examples=True,
            )
        ),
    )
    MetadataCatalog.get(catalog_name).set(thing_classes=classes)
    if evaluator_type:
        MetadataCatalog.get(catalog_name).set(evaluator_type=evaluator_type)
    return catalog_name


def clamp_bbox_to_image_size(annotations, img_width, img_height, format="xywh"):
    """
    Clamps bounding boxes in annotations to the given image dimensions.

    :param annotations: Dictionary containing bounding box coordinates in 'boxes' key.
    :param img_width: Width of the image.
    :param img_height: Height of the image.
    :param format: Format of the bounding boxes, either "xywh" or "xyxy".
    :return: Annotations with clamped bounding boxes.

    The function modifies the input annotations dictionary to clamp the bounding box coordinates
    based on the specified format, ensuring they lie within the image dimensions.
    """
    boxes = annotations["boxes"]

    if format == "xyxy":
        boxes[:, 0::2].clamp_(min=0, max=img_width - 1)
        boxes[:, 1::2].clamp_(min=0, max=img_height - 1)

    elif format == "xywh":
        # First, clamp the x and y coordinates
        boxes[:, 0].clamp_(min=0, max=img_width - 1)
        boxes[:, 1].clamp_(min=0, max=img_height - 1)
        # Then, clamp the width and height
        boxes[:, 2].clamp_(
            min=torch.tensor(0), max=img_width - boxes[:, 0] - 1
        )  # -1 since we images are zero-indexed
        boxes[:, 3].clamp_(
            min=torch.tensor(0), max=img_height - boxes[:, 1] - 1
        )  # -1 since we images are zero-indexed
    else:
        raise ValueError(f"Unsupported bounding box format: {format}")

    annotations["boxes"] = boxes
    return annotations
