import random
from typing import Dict, Optional, Union

import torch
import torchvision.transforms as transforms
import torchvision.transforms.functional as F
from PIL import Image

from .utils import convert_polygon_to_mask

TargetKey = Union["boxes", "labels", "masks", "image_id", "area", "iscrowd"]
TargetType = Dict[TargetKey, torch.Tensor]


class Compose(transforms.Compose):
    def __call__(self, image: Image, target: Optional[TargetType] = None):
        if target is None:
            return super(Compose, self).__call__(image)
        for transform in self.transforms:
            image, target = transform(image, target)
        return image, target


class RandomHorizontalFlip(object):
    def __init__(self, p: float = 0.5):
        self.p = p

    def __call__(self, image: Image, target: Optional[TargetType] = None):
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


class ColorJitter(transforms.ColorJitter):
    def __call__(self, image: Image, target: Optional[TargetType] = None):
        transform = self.get_params(self.brightness, self.contrast, self.saturation, self.hue)
        image = transform(image)
        if target is None:
            return image
        return image, target


class ToTensor(object):
    def __call__(self, image: Image, target: Optional[TargetType] = None):
        image = F.to_tensor(image)
        if target is None:
            return image
        return image, target


class ToPILImage(object):
    def __call__(self, image: Image, target: Optional[TargetType] = None):
        image = F.to_pil_image(image)
        if target is None:
            return image
        return image, target


class ConvertPolygonsToInstanceMasks(object):
    def __call__(self, image: Image, target: TargetType):
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
        masks = convert_polygon_to_mask(segmentations, h, w)

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


class ConvertPolygonsToSegmentationMask(object):
    def __call__(self, image, target):
        w, h = image.size
        image_id = target["image_id"]
        image_id = torch.tensor([image_id])

        annotations = target.pop("annotations")
        segmentations = [obj["segmentation"] for obj in annotations]
        cats = [obj["category_id"] for obj in annotations]
        if segmentations:
            masks = convert_polygon_to_mask(segmentations, h, w)
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
    def __call__(self, image, annotation):
        w, h = image.size
        segmentations = [obj["segmentation"] for obj in annotation]
        cats = [obj["category_id"] for obj in annotation]
        if segmentations:
            masks = convert_polygon_to_mask(segmentations, h, w)
            cats = torch.as_tensor(cats, dtype=masks.dtype)
            # merge all instance masks into a single segmentation map
            # with its corresponding categories
            target, _ = (masks * cats[:, None, None]).max(dim=0)
            # discard overlapping instances
            target[masks.sum(0) > 1] = 255
        else:
            target = torch.zeros((h, w), dtype=torch.uint8)
        target = Image.fromarray(target.numpy())
        return image, target
