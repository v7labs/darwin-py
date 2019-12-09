import PIL
import torch

from darwin.torch.utils import convert_polygon_to_mask


class Compose(object):
    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, target=None):
        for t in self.transforms:
            image, target = t(image, target)
        if target is not None:
            return image, target
        else:
            return image


class ConvertPolygonsToInstanceMasks(object):
    def __call__(self, image, target):
        w, h = image.size

        image_id = target["image_id"]
        image_id = torch.tensor([image_id])

        annotations = target["annotations"]

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

        target = {}
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
        target = PIL.Image.fromarray(target.numpy())
        return image, target
