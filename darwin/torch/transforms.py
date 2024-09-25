import random
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple, Union

import numpy as np
import torch
import torchvision.transforms as transforms
import torchvision.transforms.functional as F
from PIL import Image as PILImage

from darwin.torch.utils import convert_segmentation_to_mask, flatten_masks_by_category

# Optional dependency
try:
    import albumentations as A
    from albumentations import Compose
except ImportError:
    A = None

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from albumentations.pytorch import ToTensorV2

    AType = Type[ToTensorV2]
else:
    AType = Type[None]
    Compose = Type[None]

TargetKey = Literal["boxes", "labels", "mask", "masks", "image_id", "area", "iscrowd"]


TargetType = Dict[TargetKey, torch.Tensor]


class Compose(transforms.Compose):
    """
    Composes a sequence of Transformations.
    """

    def __call__(self, image: PILImage.Image, target: Optional[TargetType] = None):
        if target is None:
            return super(Compose, self).__call__(image)
        for transform in self.transforms:
            image, target = transform(image, target)
        return image, target


class RandomHorizontalFlip(transforms.RandomHorizontalFlip):
    """
    Allows for horizontal flipping of an image, randomly.
    """

    def forward(
        self, image: torch.Tensor, target: Optional[TargetType] = None
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, TargetType]]:
        """
        May or may not horizontally flip an image depending on a random factor.

        Parameters
        ----------
        image : torch.Tensor
            Image ``Tensor`` to flip.
        target : Optional[TargetType] = None
            The target.

        Returns
        -------
        Union[torch.Tensor, Tuple[torch.Tensor, TargetType]]
            Will return a single image ``Tensor`` if the flip did not happen, or a tuple of the
            image tensor and the target type if the flip did happen.

        """
        if random.random() < self.p:
            image = F.hflip(image)
            if target is None:
                return image

            if "boxes" in target:
                bbox = target["boxes"]
                bbox[:, [0, 2]] = image.size[0] - bbox[:, [2, 0]]
                target["boxes"] = bbox
            for k in ["mask", "masks"]:
                if k in target:
                    target[k] = target[k].flip(-1)
            return image, target

        if target is None:
            return image

        return image, target


class RandomVerticalFlip(transforms.RandomVerticalFlip):
    """
    Allows for vertical flipping of an image, randomly.
    """

    def forward(
        self, image: torch.Tensor, target: Optional[TargetType] = None
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, TargetType]]:
        """
        May or may not vertically flip an image depending on a random factor.

        Parameters
        ----------
        image : torch.Tensor
            Image ``Tensor`` to flip.
        target : Optional[TargetType] = None
            The target.

        Returns
        -------
        Union[torch.Tensor, Tuple[torch.Tensor, TargetType]]
            Will return a single image ``Tensor`` if the flip did not happen, or a tuple of the
            image tensor and the target type if the flip did happen.

        """
        if random.random() < self.p:
            image = F.vflip(image)
            if target is None:
                return image

            if "boxes" in target:
                bbox = target["boxes"]
                bbox[:, [1, 3]] = image.size[1] - bbox[:, [1, 3]]
                target["boxes"] = bbox
            for k in ["mask", "masks"]:
                if k in target:
                    target[k] = target[k].flip(-2)
            return image, target

        if target is None:
            return image
        return image, target


class ColorJitter(transforms.ColorJitter):
    """
    Jitters the colors of the given transformation.
    """

    def __call__(
        self, image: PILImage.Image, target: Optional[TargetType] = None
    ) -> Union[PILImage.Image, Tuple[PILImage.Image, TargetType]]:
        transform = self.get_params(
            self.brightness, self.contrast, self.saturation, self.hue
        )
        image = transform(image)
        if target is None:
            return image
        return image, target


class ToTensor(transforms.ToTensor):
    """
    Converts given ``PILImage`` to a ``Tensor``.
    """

    def __call__(
        self, image: PILImage.Image, target: Optional[TargetType] = None
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, TargetType]]:
        image_tensor: torch.Tensor = F.to_tensor(image)
        if target is None:
            return image_tensor
        return image_tensor, target


class ToPILImage(transforms.ToPILImage):
    """
    Converts given ``Tensor`` to a ``PILImage``.
    """

    def __call__(
        self, image: torch.Tensor, target: Optional[TargetType] = None
    ) -> Union[PILImage.Image, Tuple[PILImage.Image, TargetType]]:
        pil_image: PILImage.Image = F.to_pil_image(image)
        if target is None:
            return pil_image
        return pil_image, target


class Normalize(transforms.Normalize):
    """
    Normalizes the given ``Tensor``.
    """

    def __call__(
        self, tensor: torch.Tensor, target: Optional[TargetType] = None
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, TargetType]]:
        tensor = F.normalize(tensor, self.mean, self.std, self.inplace)

        if target is None:
            return tensor
        return tensor, target


class ConvertPolygonsToInstanceMasks(object):
    """
    Converts given polygon to an ``InstanceMask``.
    """

    def __call__(
        self, image: PILImage.Image, target: TargetType
    ) -> Tuple[PILImage.Image, TargetType]:
        w, h = image.size

        image_id = target["image_id"]
        image_id = torch.tensor([image_id])

        annotations = target.pop("annotations")

        annotations = [obj for obj in annotations if obj.get("iscrowd", 0) == 0]

        boxes = [obj["bbox"] for obj in annotations]
        # guard against no boxes via resizing
        boxes = torch.as_tensor(boxes, dtype=torch.float32).reshape(-1, 4)

        classes = [obj["category_id"] for obj in annotations]
        classes = torch.tensor(classes, dtype=torch.int64)

        segmentations = [obj["segmentation"] for obj in annotations]
        masks = convert_segmentation_to_mask(segmentations, h, w)

        keypoints = None
        if annotations and "keypoints" in annotations[0]:
            keypoints = [obj["keypoints"] for obj in annotations]
            keypoints = torch.as_tensor(keypoints, dtype=torch.float32)
            num_keypoints = keypoints.shape[0]
            if num_keypoints:
                keypoints = keypoints.view(num_keypoints, -1, 3)

        target["boxes"] = boxes
        target["labels"] = classes
        target["masks"] = masks
        target["image_id"] = image_id
        if keypoints is not None:
            target["keypoints"] = keypoints

        # Remove boxes with widht or height zero
        keep = (boxes[:, 3] > 0) & (boxes[:, 2] > 0)
        boxes = boxes[keep]
        classes = classes[keep]
        masks = masks[keep]
        if keypoints is not None:
            keypoints = keypoints[keep]

        # conversion to coco api
        area = torch.tensor([obj["area"] for obj in annotations])
        iscrowd = torch.tensor([obj.get("iscrowd", 0) for obj in annotations])
        target["area"] = area
        target["iscrowd"] = iscrowd

        return image, target


class ConvertPolygonsToSemanticMask(object):
    """
    Converts given polygon to an ``SemanticMask``.
    """

    def __call__(
        self, image: PILImage.Image, target: TargetType
    ) -> Tuple[PILImage.Image, TargetType]:
        w, h = image.size
        image_id = target["image_id"]
        image_id = torch.tensor([image_id])

        annotations = target.pop("annotations")
        segmentations = [obj["segmentation"] for obj in annotations]
        cats = [obj["category_id"] for obj in annotations]
        if segmentations:
            masks = convert_segmentation_to_mask(segmentations, h, w)
            # merge all instance masks into a single segmentation map
            # with its corresponding categories
            mask = flatten_masks_by_category(masks, cats)

        else:
            mask = torch.zeros((h, w), dtype=torch.uint8)

        target["mask"] = mask
        target["image_id"] = image_id
        return image, target


class ConvertPolygonToMask(object):
    """
    Converts given polygon to a ``Mask``.
    """

    def __call__(
        self, image: PILImage.Image, annotation: Dict[str, Any]
    ) -> Tuple[PILImage.Image, PILImage.Image]:
        w, h = image.size
        segmentations = [obj["segmentation"] for obj in annotation]
        cats = [obj["category_id"] for obj in annotation]
        if segmentations:
            masks = convert_segmentation_to_mask(segmentations, h, w)
            # merge all instance masks into a single segmentation map
            # with its corresponding categories
            target = flatten_masks_by_category(masks, cats)

        else:
            target = torch.zeros((h, w), dtype=torch.uint8)
        target = PILImage.fromarray(target.numpy())
        return image, target


class AlbumentationsTransform:
    """
    Wrapper class for Albumentations augmentations.
    """

    def __init__(self, transform: Compose):
        self._check_albumentaion_dependency()
        self.transform = transform

    @classmethod
    def from_path(cls, config_path: str) -> "AlbumentationsTransform":
        config_path = Path(config_path)
        try:
            transform = A.load(str(config_path))
            return cls(transform)
        except Exception as e:
            raise ValueError(f"Invalid config path: {config_path}. Error: {e}")

    @classmethod
    def from_dict(cls, alb_dict: dict) -> "AlbumentationsTransform":
        try:
            transform = A.from_dict(alb_dict)
            return cls(transform)
        except Exception as e:
            raise ValueError(f"Invalid albumentations dictionary. Error: {e}")

    def __call__(self, image, annotation: dict = None) -> tuple:
        np_image = np.array(image)
        if annotation is None:
            annotation_dict = {}
        else:
            annotation_dict = annotation

        albu_data = self._pre_process(np_image, annotation_dict)
        transformed_data = self.transform(**albu_data)
        image, transformed_annotation = self._post_process(
            transformed_data, annotation_dict
        )

        if annotation is None:
            return image

        return image, transformed_annotation

    def _pre_process(self, image: np.ndarray, annotation: dict) -> dict:
        """
        Prepare image and annotation for albumentations transformation.
        """
        albumentation_dict = {"image": image}

        boxes = annotation.get("boxes")
        if boxes is not None:
            albumentation_dict["bboxes"] = boxes.numpy().tolist()

        labels = annotation.get("labels")
        if labels is not None:
            albumentation_dict["labels"] = labels.tolist()

        masks = annotation.get("masks")
        if (
            masks is not None and masks.numel() > 0
        ):  # using numel() to check if tensor is non-empty
            if isinstance(masks, torch.Tensor):
                masks = masks.numpy()
            if masks.ndim == 3:  # Ensure masks is a list of numpy arrays
                masks = [masks[i] for i in range(masks.shape[0])]
            albumentation_dict["masks"] = masks

        return albumentation_dict

    def _post_process(self, albumentation_output: dict, annotation: dict) -> tuple:
        """
        Process the output of albumentations transformation back to desired format.
        """
        output_annotation = {}
        image = albumentation_output["image"]

        bboxes = albumentation_output.get("bboxes")
        if bboxes is not None:
            output_annotation["boxes"] = torch.tensor(bboxes)

        labels = albumentation_output.get("labels")
        if labels is not None:
            output_annotation["labels"] = torch.tensor(labels)

        masks = albumentation_output.get("masks")
        if masks is not None:
            if isinstance(masks[0], np.ndarray):
                output_annotation["masks"] = torch.tensor(np.array(masks))
            else:
                output_annotation["masks"] = torch.stack(masks)
        elif "masks" in annotation:
            output_annotation["masks"] = torch.tensor([])

        if "area" in annotation:
            if "masks" in output_annotation and output_annotation["masks"].numel() > 0:
                output_annotation["area"] = torch.sum(
                    output_annotation["masks"], dim=[1, 2]
                )
            elif "boxes" in output_annotation and len(output_annotation["boxes"]) > 0:
                output_annotation["area"] = (
                    output_annotation["boxes"][:, 2] * output_annotation["boxes"][:, 3]
                )
            else:
                output_annotation["area"] = torch.tensor([])

        # Copy other metadata from original annotation
        for key, value in annotation.items():
            output_annotation.setdefault(key, value)

        return image, output_annotation

    def _check_albumentaion_dependency(self):
        if A is None:
            raise ImportError(
                "The albumentations library is not installed. "
                "To use this function, install it with pip install albumentations, "
                "or install the ml extras of this package."
            )
