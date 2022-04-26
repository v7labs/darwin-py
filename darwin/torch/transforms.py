import random
from typing import Any, Dict, Optional, Tuple, Union

import torchvision.transforms as transforms
import torchvision.transforms.functional as F
from darwin.torch.utils import convert_segmentation_to_mask
from PIL import Image as PILImage

import torch

TargetKey = Union["boxes", "labels", "masks", "image_id", "area", "iscrowd"]
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
            if "masks" in target:
                target["masks"] = target["masks"].flip(-1)
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
            if "masks" in target:
                target["masks"] = target["masks"].flip(-2)
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
        transform = self.get_params(self.brightness, self.contrast, self.saturation, self.hue)
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

    def __call__(self, image: PILImage.Image, target: TargetType) -> Tuple[PILImage.Image, TargetType]:
        w, h = image.size

        image_id = target["image_id"]
        image_id = torch.tensor([image_id])

        annotations = target.pop("annotations")

        annotations = [obj for obj in annotations if obj.get("iscrowd", 0) == 0]

        boxes = [obj["bbox"] for obj in annotations]
        # guard against no boxes via resizing
        boxes = torch.as_tensor(boxes, dtype=torch.float32).reshape(-1, 4)
        boxes[:, 2:] += boxes[:, :2]
        boxes[:, 0::2].clamp_(min=0, max=w)
        boxes[:, 1::2].clamp_(min=0, max=h)

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

        keep = (boxes[:, 3] > boxes[:, 1]) & (boxes[:, 2] > boxes[:, 0])
        boxes = boxes[keep]
        classes = classes[keep]
        masks = masks[keep]
        if keypoints is not None:
            keypoints = keypoints[keep]

        target["boxes"] = boxes
        target["labels"] = classes
        target["masks"] = masks
        target["image_id"] = image_id
        if keypoints is not None:
            target["keypoints"] = keypoints

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

    def __call__(self, image: PILImage.Image, target: TargetType) -> Tuple[PILImage.Image, TargetType]:
        w, h = image.size
        image_id = target["image_id"]
        image_id = torch.tensor([image_id])

        annotations = target.pop("annotations")
        segmentations = [obj["segmentation"] for obj in annotations]
        cats = [obj["category_id"] for obj in annotations]
        if segmentations:
            masks = convert_segmentation_to_mask(segmentations, h, w)
            cats = torch.as_tensor(cats, dtype=masks.dtype)
            # merge all instance masks into a single segmentation map
            # with its corresponding categories
            mask, _ = (masks * cats[:, None, None]).max(dim=0)
            # discard overlapping instances
            mask[masks.sum(0) > 1] = 255
        else:
            mask = torch.zeros((h, w), dtype=torch.uint8)

        target["mask"] = mask
        target["image_id"] = image_id
        return image, target


class ConvertPolygonToMask(object):
    """
    Converts given polygon to a ``Mask``.
    """

    def __call__(self, image: PILImage.Image, annotation: Dict[str, Any]) -> Tuple[PILImage.Image, PILImage.Image]:
        w, h = image.size
        segmentations = [obj["segmentation"] for obj in annotation]
        cats = [obj["category_id"] for obj in annotation]
        if segmentations:
            masks = convert_segmentation_to_mask(segmentations, h, w)
            cats = torch.as_tensor(cats, dtype=masks.dtype)
            # merge all instance masks into a single segmentation map
            # with its corresponding categories
            target, _ = (masks * cats[:, None, None]).max(dim=0)
            # discard overlapping instances
            target[masks.sum(0) > 1] = 255
        else:
            target = torch.zeros((h, w), dtype=torch.uint8)
        target = PILImage.fromarray(target.numpy())
        return image, target
