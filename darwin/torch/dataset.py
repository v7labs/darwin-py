import json
import random
from pathlib import Path
from typing import Optional

import numpy as np

from darwin.client import Client
from darwin.torch.utils import (
    convert_polygon_to_sequence,
    fetch_darwin_dataset,
    load_pil_image,
    polygon_area,
)

def get_dataset(
        dataset_name: str,
        image_set: Optional[str] = "train",
        mode: Optional[str] = "raw",
        transforms: Optional = None,
        client: Optional[Client] = None,
        **kwargs,
):
    """
    Pulls a dataset from Darwin and returns a Dataset class that can be used with a PyTorch dataloader

    Parameters
    ----------
    dataset_name : str
        Identifier of the dataset in Darwin
    image_set : str
        Split set, values must be either 'train', 'val' or 'test'
    mode : str
        selects the dataset type [image_classification, instance_segmentation, semantic_segmentation]
    transforms :  [torchvision.transforms]
        List of PyTorch transforms
    client:  Client
        Darwin's client

    Returns
    -------
    Dataset
        Dataset class
    """

    root, split_id = fetch_darwin_dataset(dataset_name, client, **kwargs)

    if mode == "raw":
        return Dataset(
            root=root, image_set=image_set, split_id=split_id, transforms=transforms
        )

    if mode == "classification":
        return ClassificationDataset(
            root=root, image_set=image_set, split_id=split_id, transforms=transforms
        )

    if mode == "instance_segmentation":
        import darwin.torch.transforms as T
        if transforms is None:
            transforms = []
        transforms.insert(0, T.ConvertPolysToInstanceMasks())
        transforms = T.Compose(transforms)
        return InstanceSegmentationDataset(
            root=root, image_set=image_set, split_id=split_id, transforms=transforms
        )

    if mode == "semantic_segmentation":
        import darwin.torch.transforms as T
        if transforms is None:
            transforms = []
        transforms.insert(0, T.ConvertPolysToMask())
        transforms = T.Compose(transforms)
        return SemanticSegmentationDataset(
            root=root, image_set=image_set, split_id=split_id, transforms=transforms
        )

    raise ValueError("Dataset type {mode} not supported.")


class Dataset(object):
    def __init__(self, root: Path, image_set: str, split_id: Optional[str] = None, transforms=None):
        self.root = root
        self.image_set = image_set
        self.transforms = transforms
        self.images_path = []
        self.annotations_path = []
        self.classes = None
        self.original_images_path = None
        self.original_annotations_path = None
        self.original_classes = None

        if self.image_set not in ["train", "val", "test"]:
            raise ValueError(f"Unknown partition {self.image_set}")

        path_to_lists = self.root / "lists"
        if split_id is not None:
            path_to_lists /= split_id
        file_partition = path_to_lists / f"{self.image_set}.txt"

        if not file_partition.exists():
            raise FileNotFoundError(
                "Could not find partition {image_set} in {path_to_lists}. (Is the percentage larger than 0?)"
            )

        extensions = ["jpg", "jpeg", "png"]
        stems = [e.strip() for e in open(str(file_partition))]
        for stem in stems:
            annotation_path = self.root / f"annotations/{stem}.json"
            for extension in extensions:
                image_path = self.root / f"images/{stem}.{extension}"
                if image_path.is_file():
                    self.images_path.append(image_path)
                    self.annotations_path.append(annotation_path)
                    break
        if len(self.images_path) == 0:
            raise ValueError(f"could not find any {extensions} file in {self.root/'images'}")
        if len(self.images_path) != len(self.annotations_path):
            raise ValueError(f"some annotations ({len(self.annotations_path)}) "
                             f"do not have a corresponding image ({len(self.images_path)})")

    def subsample(self, perc: float):
        num = int(len(self.annotations_path) * perc)
        #TODO warning this does not protect from x-contamination! See PR
        indices = random.sample(range(len(self.annotations_path)), num)
        self.original_images_path = self.images_path
        self.images_path = [self.images_path[i] for i in indices]
        self.original_annotations_path = self.annotations_path
        self.annotations_path = [self.annotations_path[i] for i in indices]

    def extend(self, db, extend_classes=False):
        if self.classes != db.classes and not extend_classes:
            raise ValueError(
                "Operation dataset_a + dataset_b could not be computed: classes should match. \
                             Use flag extend_classes=True to combine both lists of classes."
            )
        self.classes = list(set(self.classes).union(set(db.classes)))

        self.original_images_path = self.images_path
        self.images_path += db.images
        self.original_annotations_path = self.annotations_path
        self.annotations_path += db.annotations
        return self

    def _map_annotation(self, index: int):
        """
        Load an annotation and filter out the extra classes according to what
        specified in `self.classes`

        Parameters
        ----------
        index : int
            Index of the annotation to read

        Returns
        -------
        dict
        A new dictionary containing the index and the filtered annotation
        """
        with open(str(self.annotations_path[index])) as f:
            annotation = json.load(f)["annotations"]

        if self.classes is None:
            raise ValueError(f"No classes have been specified yet (self.classes is still none!).")

        # Filter out unused classes
        annotation = [a for a in annotation if a["name"] in self.classes]
        return {"image_id": index,
                "annotations": annotation}

    def __getitem__(self, index: int):
        # load images and masks
        img = load_pil_image(self.images_path[index])
        target = self._map_annotation(index)

        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def __add__(self, db):
        if self.classes != db.classes:
            raise ValueError(
                "Operation dataset_a + dataset_b could not be computed: classes should match. \
                             Use dataset_a.extend(dataset_b, extend_classes=True) to combine both lists of classes"
            )
        self.original_images_path = self.images_path
        self.images_path += db.images
        self.original_annotations_path = self.annotations_path
        self.annotations_path += db.annotations
        return self

    def __mul__(self, percentage: float):
        self.subsample(percentage)

    def __len__(self):
        return len(self.images_path)

    def __str__(self):
        format_string = (
            f"{self.__class__.__name__}():\n"
            f"  Root: {self.root}\n"
            f"  Number of images: {len(self.images_path)}"
        )
        return format_string


class ClassificationDataset(Dataset):
    def __init__(self, root: Path, image_set: str, split_id: Optional[str] = None, transforms=None):
        super(ClassificationDataset, self).__init__(root, image_set, split_id, transforms)
        self.classes = [e.strip() for e in open(str(root / "lists/classes_tags.txt"))]

    def _map_annotation(self, index: int):
        with open(str(self.annotations_path[index])) as f:
            annotation = json.load(f)["annotations"]
            for obj in annotation:
                if "tag" in obj:
                    return {"category_id": self.classes.index(obj["name"])}


class InstanceSegmentationDataset(Dataset):
    def __init__(self, root: Path, image_set: str, split_id: Optional[str] = None, transforms=None):
        super(InstanceSegmentationDataset, self).__init__(root, image_set, split_id, transforms)
        self.classes = [e.strip() for e in open(str(root / "lists/classes_masks.txt"))]

    def _map_annotation(self, index: int):
        with open(str(self.annotations_path[index])) as f:
            anno = json.load(f)["annotations"]

        # Filter out unused classes
        anno = [obj for obj in anno if obj["name"] in self.classes]

        target = []
        for obj in anno:
            new_obj = {"image_id": index,
                       "iscrowd": 0,
                       "category_id": self.classes.index(obj["name"]),
                       "segmentation": [convert_polygon_to_sequence(obj["polygon"]["path"])]}

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
                raise ValueError(
                    f"polygon's area should be <= bbox's area. Failed {poly_area} <= {bbox_area}"
                )
            new_obj["area"] = poly_area

            target.append(new_obj)

        return {'image_id':index,
                'annotations':target}


class SemanticSegmentationDataset(Dataset):
    def __init__(self, root: Path, image_set: str, split_id: Optional[str] = None, transforms=None):
        super(SemanticSegmentationDataset, self).__init__(root, image_set, split_id, transforms)
        self.classes = [e.strip() for e in open(str(root / "lists/classes_masks.txt"))]
        if self.classes[0] == "__background__":
            self.classes = self.classes[1:]

    def _map_annotation(self, index: int):
        with open(str(self.annotations_path[index])) as f:
            annotation = json.load(f)["annotations"]

        # Filter out unused classes
        annotation = [obj for obj in annotation if obj["name"] in self.classes]

        target = []
        for obj in annotation:
            target.append({"category_id": self.classes.index(obj["name"]),
                           "segmentation": [convert_polygon_to_sequence(obj["polygon"]["path"])]})
        return target
