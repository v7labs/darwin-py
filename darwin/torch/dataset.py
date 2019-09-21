import os
import numpy as np
import torch
import random
from pathlib import Path
import json
from typing import Optional

from darwin.client import Client
from darwin.torch.utils import load_pil_image, convert_polygon_to_sequence, polygon_area, fetch_darwin_dataset


def get_dataset(
    dataset_name: str,
    image_set: Optional[str] = "train",
    mode: Optional[str] = "raw",
    transforms: Optional = None,
    poly_to_mask: Optional[bool] = False,
    client: Optional[Client] = None,
    **kwargs
):
    '''
    Pulls a dataset from Darwin and returns a Dataset class that can be used with a Pytorch dataloader

    Input:
        dataset_name: Identifier of the dataset in Darwin
        image_set: Split set [train, val, test]
        mode: selects the dataset type [image_classification, instance_segmentation, semantic_segmentation]
        transforms: List of Pytorch's transforms
        client: Darwin's client
        val_percentage: percentage of images used in the validation set
        test_percentage: percentage of images used in the validation set
        force_fetching: discard local dataset and pull again from Darwin
        force_resplit: discard previous split and create a new one
        split_seed: fix seed for random split creation

    Output:
        Dataset class
    '''

    root, split_id = fetch_darwin_dataset(dataset_name, client, **kwargs)

    if mode == "raw":
        dataset = Dataset(root, image_set=image_set, split_id=split_id, transforms=transforms)
    elif mode == "classification":
        dataset = ClassificationDataset(root, image_set=image_set, split_id=split_id, transforms=transforms)
    elif mode == "instance_segmentation":
        import darwin.torch.transforms as T
        trfs = [T.ConvertPolysToInstanceMasks()]
        if transforms is not None:
            trfs.append(transforms)
        transforms = T.Compose(trfs)
        dataset = InstanceSegmentationDataset(root, image_set=image_set, split_id=split_id, transforms=transforms)
    elif mode == "semantic_segmentation":
        import darwin.torch.transforms as T
        trfs = [T.ConvertPolysToMask()]
        if transforms is not None:
            trfs.append(transforms)
        transforms = T.Compose(trfs)
        dataset = SemanticSegmentationDataset(root, image_set=image_set, split_id=split_id, transforms=transforms)
    else:
        raise ValueError("Dataset type {mode} not supported.")

    return dataset


class Dataset(object):
    def __init__(
        self,
        root: Path,
        image_set: str,
        split_id: Optional[str] = None,
        transforms=None
    ):
        self.root = root
        self.transforms = transforms
        self.image_set = image_set

        if self.image_set not in ["train", "val", "test"]:
            raise ValueError("Unknown partition {self.image_set}")

        path_to_lists = root / "lists"
        if split_id is not None:
            path_to_lists /= split_id
        file_partition = path_to_lists / f"{image_set}.txt"

        if not file_partition.exists():
            raise FileNotFoundError("Could not find partition {image_set} in {path_to_lists}. (Is the percentage larger than 0?)")
        stems = [e.strip() for e in open(file_partition)]

        exts = ["jpg", "jpeg", "png"]
        self.annotations, self.images = [], []
        for s in stems:
            annot_path = root / f"annotations/{s}.json"
            for ext in exts:
                im_path = root / f"images/{s}.{ext}"
                if im_path.is_file():
                    self.images.append(im_path)
                    self.annotations.append(annot_path)
                    break
        if len(self.images) == 0:
            raise ValueError(f"could not find any {exts} file in {root/'images'}")

    def __getitem__(self, idx: int):
        # load images ad masks
        img = load_pil_image(self.images[idx])
        target = self._load_anno_and_remap(idx)

        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def _load_anno_and_remap(self, idx: int):
        with open(self.annotations[idx]) as f:
            anno = json.load(f)['annotations']

        # Filter out unused classes
        anno = [obj for obj in anno if obj["name"] in self.classes]

        res = dict(image_id=idx, annotations=anno)
        return res

    def __len__(self):
        return len(self.images)

    def subsample(self, perc: float):
        num = int(len(self.annotations) * perc)
        indices = random.sample(range(len(self.annotations)), num)
        self.orig_imgs = self.images
        self.images = [self.images[i] for i in indices]
        self.orig_annotations = self.annotations
        self.annotations = [self.annotations[i] for i in indices]

    def __add__(self, db):
        if self.classes != db.classes:
            raise ValueError('Operation dataset_a + dataset_b could not be computed: classes should match. \
                             Use dataset_a.extend(dataset_b, extend_classes=True) to combine both lists of classes')
        self.orig_imgs = self.images
        self.images += db.images
        self.orig_annotations = self.annotations
        self.annotations += db.annotations
        return self

    def extended(self, db, extend_classes=False):
        if self.classes != db.classes and not extend_classes:
            raise ValueError('Operation dataset_a + dataset_b could not be computed: classes should match. \
                             Use flag extend_classes=True to combine both lists of classes.')
        elif self.classes != db.classes and extend_classes:
            self.orig_classes = self.classes
            for c in db.classes:
                if c not in self.classes:
                    self.classes.append(c)

        self.orig_imgs = self.images
        self.images += db.images
        self.orig_annotations = self.annotations
        self.annotations += db.annotations
        return self

    def __mul__(self, perc: float):
        self.subsample(perc)

    def __str__(self):
        format_string = (
            f"{self.__class__.__name__}():\n"
            f"  Root: {self.root}\n"
            f"  Number of images: {len(self.images)}"
            )
        return format_string


class ClassificationDataset(Dataset):
    def __init__(
        self,
        root: Path,
        image_set: str,
        split_id: Optional[str] = None,
        transforms=None
    ):
        super(ClassificationDataset, self).__init__(root, image_set, split_id, transforms)
        self.classes = [e.strip() for e in open(root / 'lists/classes_tags.txt')]

    def _load_anno_and_remap(self, idx: int):
        with open(self.annotations[idx]) as f:
            anno = json.load(f)['annotations']
            for obj in anno:
                if "tag" in obj:
                    target = {"category_id": self.classes.index(obj["name"])}
        return target


class InstanceSegmentationDataset(Dataset):
    def __init__(
        self,
        root: Path,
        image_set: str,
        split_id: Optional[str] = None,
        transforms=None
    ):
        super(InstanceSegmentationDataset, self).__init__(root, image_set, split_id, transforms)
        self.classes = [e.strip() for e in open(root / 'lists/classes_masks.txt')]

    def _load_anno_and_remap(self, idx: int):
        with open(self.annotations[idx]) as f:
            anno = json.load(f)['annotations']

        # Filter out unused classes
        anno = [obj for obj in anno if obj["name"] in self.classes]

        target = []
        for obj in anno:
            new_obj = {"image_id": idx, "iscrowd": 0}
            new_obj["category_id"] = self.classes.index(obj["name"])
            new_obj["segmentation"] = [convert_polygon_to_sequence(obj["polygon"]["path"])]
            seg = np.array(new_obj["segmentation"][0])
            xcoords = seg[0::2]
            ycoords = seg[1::2]
            x = np.max((0, np.min(xcoords) - 1))
            y = np.max((0, np.min(ycoords) - 1))
            w = (np.max(xcoords) - x) + 1
            h = (np.max(ycoords) - y) + 1
            new_obj["bbox"] = [x, y, w, h]
            poly_area = polygon_area(xcoords, ycoords)
            bbox_area = w * h
            if poly_area > bbox_area:
                raise ValueError(f"polygon's area should be <= bbox's area. Failed {poly_area} <= {bbox_area}")
            new_obj["area"] = poly_area
            target.append(new_obj)

        res = dict(image_id=idx, annotations=target)

        return res


class SemanticSegmentationDataset(Dataset):
    def __init__(
        self,
        root: Path,
        image_set: str,
        split_id: Optional[str] = None,
        transforms=None
    ):
        super(SemanticSegmentationDataset, self).__init__(root, image_set, split_id, transforms)
        self.classes = [e.strip() for e in open(root / 'lists/classes_masks.txt')]
        if self.classes[0] == "__background__":
            self.classes = self.classes[1:]

    def _load_anno_and_remap(self, idx: int):
        with open(self.annotations[idx]) as f:
            anno = json.load(f)['annotations']

        # Filter out unused classes
        anno = [obj for obj in anno if obj["name"] in self.classes]

        target = []
        for obj in anno:
            new_obj = {}
            new_obj["category_id"] = self.classes.index(obj["name"])
            new_obj["segmentation"] = [convert_polygon_to_sequence(obj["polygon"]["path"])]
            target.append(new_obj)

        return target
