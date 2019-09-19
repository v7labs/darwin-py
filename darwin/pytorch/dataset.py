import os
import numpy as np
import torch
import random
from pathlib import Path
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from darwin.client import Client
from darwin.pytorch.utils import load_pil_image, convert_polygon_to_sequence, polygon_area, fetch_darwin_dataset


def get_dataset(
    dataset_id: str,
    image_set: Optional[str] = "train",
    transforms: Optional = None,
    poly_to_mask: Optional[bool] = False,
    client: Optional[Client] = None,
    **kwargs
):
    '''
    Pulls locally a dataset from Darwin and returns a Dataset class that can be used with a Pytorch dataloader

    Input:
    - dataset_id: Identifier of the dataset
    - image_set: Split set [train, val, test]
    - transforms: List of Pytorch's transforms
    - poly_to_mask: if True converts the polygons into masks
    - client: Darwin's client

    Output:
    - Pytorch's dataset
    '''

    root, split_id = fetch_darwin_dataset(dataset_id, client, **kwargs)

    if poly_to_mask:
        import darwin.pytorch.transforms as T
        trfs = [T.ConvertPolysToMask()]
        if transforms is not None:
            trfs.append(transforms)
        transforms = T.Compose(trfs)

    return Dataset(root, image_set=image_set, split_id=split_id, transforms=transforms)


class Dataset(object):
    def __init__(
        self,
        root: Path,
        image_set: Optional[str] = "train",
        split_id: Optional[str] = None,
        transforms=None
    ):
        self.root = root
        self.transforms = transforms
        self.image_set = image_set
        self.classes = [e.strip() for e in open(root / 'lists/classes.txt')]

        self.annotations, self.images = [], []
        if split_id is not None:
            path_to_lists = f"lists/{split_id}"
        else:
            path_to_lists = "lists"
        stems = [e.strip() for e in open(root / path_to_lists / f"{image_set}.txt")]
        exts = ["jpg", "jpeg", "png"]
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

        target = dict(image_id=idx, annotations=target)
        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def _load_anno_and_remap(self, idx):
        with open(self.annotations[idx]) as f:
            anno = json.load(f)['annotations']

        # Filter out unused classes
        anno = [obj for obj in anno if obj["name"] in self.classes]

        res = []
        for obj in anno:
            new_obj = {"image_id": idx, "iscrowd": 0}
            new_obj["category_id"] = self.classes.index(obj["name"])
            new_obj["segmentation"] = [convert_polygon_to_sequence(obj["polygon"]["path"])]
            seg = np.array(new_obj["segmentation"][0])
            xcoords = seg[0::2]
            ycoords = seg[1::2]
            x = np.min(xcoords)
            y = np.min(ycoords)
            w = np.max(xcoords) - x
            h = np.max(ycoords) - y
            new_obj["bbox"] = [x, y, w, h]
            area = polygon_area(xcoords, ycoords)
            assert area <= w * h, f"polygon's area should be smaller that bbox's area. Failed {area} <= {w*h}"
            new_obj["area"] = area
            res.append(new_obj)

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
        self.images += db.images
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
