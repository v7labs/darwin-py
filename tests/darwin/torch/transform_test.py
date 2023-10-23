from ast import Tuple

import numpy as np
import pytest
import torch
from albumentations import BboxParams, Compose, HorizontalFlip, Resize
from PIL import Image

from darwin.torch.transforms import AlbumentationsTransform

# Sample data
SAMPLE_IMAGE = Image.new("RGB", (100, 100))
SAMPLE_ANNOTATION = {
    "boxes": torch.tensor([[25, 25, 75, 75]]),
    "labels": torch.tensor([1]),
    "area": torch.tensor([2500.0]),
    "iscrowd": torch.tensor([0]),
}

SAMPLE_ANNOTATION_OOB = {
    "boxes": torch.tensor([[25, 25, 105, 105]]),  # Out of bounds
    "labels": torch.tensor([1]),
    "area": torch.tensor([2500.0]),
    "iscrowd": torch.tensor([0]),
}

SAMPLE_ANNOTATION_WITH_MASKS = {
    **SAMPLE_ANNOTATION,
    "masks": torch.ones((1, 100, 100)),
}

SAMPLE_EMPTY_ANNOTATION = {
    "boxes": torch.tensor([]),  # Out of bounds
    "labels": torch.tensor([]),
    "area": torch.tensor([]),
    "iscrowd": torch.tensor([]),
}

SAMPLE_EMPTY_ANNOTATION_WITH_MASKS = {
    **SAMPLE_EMPTY_ANNOTATION,
    "masks": torch.tensor([]),
}


EXAMPLE_IMAGE_TRANSFORM = Compose([HorizontalFlip(p=1)])

EXAMPLE_BOX_TRANSFORM = Compose(
    [HorizontalFlip(p=1)],
    bbox_params=BboxParams(format="coco", label_fields=["labels"]),
)

EXAMPLE_TRANSFORM_RESIZE = Compose(
    [Resize(50, 50)],
    bbox_params=BboxParams(format="coco", label_fields=["labels"]),
)

class TestAlbumentationsTransform:
    def test_init(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        assert isinstance(at, AlbumentationsTransform)

    def test_from_path_invalid(self):
        with pytest.raises(ValueError):
            AlbumentationsTransform.from_path("invalid/path/to/config.yml")

    def test_from_dict_invalid(self):
        with pytest.raises(ValueError):
            AlbumentationsTransform.from_dict({"invalid": "config"})

    def test_transformations(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        image, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION)
        assert annotation["boxes"][0, 0] != SAMPLE_ANNOTATION["boxes"][0, 0]

    def test_transformations_resize(self):
        transformations = EXAMPLE_TRANSFORM_RESIZE
        at = AlbumentationsTransform(transformations)
        image, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION)
        assert image.shape[:2] == (50, 50)  # We only check the height and width

    def test_boxes_out_of_bounds(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        with pytest.raises(ValueError):
            _, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION_OOB)  # Expecting the ValueError due to out of bounds

    def test_transform_with_masks(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        _, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION_WITH_MASKS)
        assert "masks" in annotation
        assert annotation["masks"].shape[0] == 1

    def test_area_calculation_with_masks(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        _, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION_WITH_MASKS)
        assert annotation["area"] == torch.sum(annotation["masks"])

    def test_area_calculation_without_masks(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        _, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION)
        area = annotation["boxes"][0, 2] * annotation["boxes"][0, 3]

        assert torch.isclose(annotation["area"], area.unsqueeze(0), atol=1e-5)  # Using isclose for floating point comparison

    def test_iscrowd_unchanged(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        _, annotation = at(SAMPLE_IMAGE, SAMPLE_ANNOTATION)
        assert "iscrowd" in annotation
        assert annotation["iscrowd"] == SAMPLE_ANNOTATION["iscrowd"]

    def test_image_only(self):
        transformations = EXAMPLE_IMAGE_TRANSFORM
        at = AlbumentationsTransform(transformations)
        
        image = at(SAMPLE_IMAGE)
        assert image is not None
        assert not isinstance(image, Tuple)
        print(type(image))
        assert isinstance(image, np.ndarray)


    def test_bbox_with_empty_annotation(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        image, annotation = at(SAMPLE_IMAGE, SAMPLE_EMPTY_ANNOTATION)

        for key in SAMPLE_EMPTY_ANNOTATION:
            assert key in annotation.keys()
            assert len(annotation[key]) == 0

    def test_mask_with_empty_annotation(self):
        transformations = EXAMPLE_BOX_TRANSFORM
        at = AlbumentationsTransform(transformations)
        image, annotation = at(SAMPLE_IMAGE, SAMPLE_EMPTY_ANNOTATION_WITH_MASKS)

        for key in SAMPLE_EMPTY_ANNOTATION_WITH_MASKS:
            assert key in annotation.keys()
            assert len(annotation[key]) == 0
        

if __name__ == "__main__":
    pytest.run()
