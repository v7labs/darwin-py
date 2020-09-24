import sys
from typing import List, Optional

import numpy as np
import torch
from upolygon import draw_polygon

from darwin.cli_functions import _error, _load_client
from darwin.dataset.identifier import DatasetIdentifier


def convert_segmentation_to_mask(segmentations: List[List[float]], height: int, width: int):
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
        mask = torch.zeros((height, width)).numpy().astype(np.uint8)
        masks.append(torch.from_numpy(np.asarray(draw_polygon(mask, contour, 1))))
    return torch.stack(masks)


def polygon_area(x: np.ndarray, y: np.ndarray) -> float:
    """
    Returns the area of the input polygon, represented with two numpy arrays
    for x and y coordinates.
    """
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def collate_fn(batch):
    return tuple(zip(*batch))


def detectron2_register_dataset(
    dataset_slug: str,
    partition: Optional[str] = None,
    split: Optional[str] = "default",
    split_type: Optional[str] = "stratified",
    evaluator_type: Optional[str] = None,
):
    """ Registers a local Darwin-formatted dataset in Detectron2

    Parameters
    ----------
    dataset_slug: str
        Dataset slug
    partition: str
        Selects one of the partitions [train, val, test]
    split
        Selects the split that defines the percetages used (use 'default' to select the default split)
    split_type: str
        Heuristic used to do the split [random, stratified]
    evaluator_type: str
        Evaluator to be used in the val and test sets
    """
    try:
        from detectron2.data import DatasetCatalog, MetadataCatalog
    except ImportError:
        print("Detectron2 not found.")
        sys.exit(1)
    from darwin.dataset.utils import get_annotations, get_classes

    identifier = DatasetIdentifier.parse(dataset_slug)
    client = _load_client(offline=True)

    for dataset_path in client.list_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == dataset_path.name:
            catalog_name = f"darwin_{identifier.dataset_slug}"
            if partition:
                catalog_name += f"_{partition}"
            classes = get_classes(dataset_path, annotation_type="polygon")
            DatasetCatalog.register(
                catalog_name,
                lambda partition=partition: list(
                    get_annotations(
                        dataset_path,
                        partition=partition,
                        split_type=split_type,
                        release_name=identifier.version,
                        annotation_type="polygon",
                        annotation_format="coco",
                    )
                ),
            )
            MetadataCatalog.get(catalog_name).set(thing_classes=classes)
            if evaluator_type:
                MetadataCatalog.get(catalog_name).set(evaluator_type=evaluator_type)
            return catalog_name

    _error(
        f"Dataset '{identifier.dataset_slug}' does not exist locally. "
        f"Use 'darwin dataset remote' to see all the available datasets, "
        f"and 'darwin dataset pull' to pull them."
    )
