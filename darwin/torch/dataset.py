import json
from pathlib import Path
from typing import List, Optional

import numpy as np

import darwin.torch.transforms as T
from darwin.torch.utils import (
    convert_polygon_to_sequence,
    load_pil_image,
    polygon_area,
)

class Dataset(object):
    def __init__(self, dataset, split: Path, transforms: Optional[List] = None):
        """ Creates a dataset

        Parameters
        ----------
        dataset : TODO
            Dataset to load
        split : Path
            Path to the *.txt file containing the list of files for this split.
        transforms : list[torchvision.transforms]
            List of PyTorch transforms
        """
        self.dataset = dataset
        self.split = split
        self.transforms = transforms
        self.images_path = []
        self.annotations_path = []
        self.classes = None
        self.original_classes = None
        self.original_images_path = None
        self.original_annotations_path = None

        #Compose the transform if necessary
        if self.transforms is not None:
            self.transforms = T.Compose(transforms)

        # Populate internal lists of annotations and images paths
        if not self.split.exists():
            raise FileNotFoundError(f"Could not find partition {self.split}"
                                    f" in {self.dataset.local_path}.")
        extensions = ["jpg", "jpeg", "png"]
        stems = (e.strip() for e in open(str(self.split)))
        for stem in stems:
            annotation_path = self.dataset.local_path / f"annotations/{stem}.json"
            for extension in extensions:
                image_path = self.dataset.local_path / f"images/{stem}.{extension}"
                if image_path.is_file():
                    self.images_path.append(image_path)
                    self.annotations_path.append(annotation_path)
                    break
        if len(self.images_path) == 0:
            raise ValueError(f"Could not find any {extensions} file"
                             f" in {self.dataset.local_path/'images'}")
        if len(self.images_path) != len(self.annotations_path):
            raise ValueError(f"Some annotations ({len(self.annotations_path)}) "
                             f"do not have a corresponding image ({len(self.images_path)})")
        assert len(self.images_path) == len(self.annotations_path)

    def extend(self, ds, extend_classes: bool = False):
        """Extends the current dataset with another one

        Parameters
        ----------
        ds : Dataset
            Dataset to merge
        extend_classes : bool
            Extend the current set of classes by merging with the passed dataset ones

        Returns
        -------
        Dataset
            self
        """
        if self.classes != ds.classes and not extend_classes:
            raise ValueError(f"Operation dataset_a + dataset_b could not be computed: classes "
                             f"should match. Use flag extend_classes=True to combine both lists "
                             f"of classes.")
        self.classes = list(set(self.classes).union(set(ds.classes)))

        self.original_images_path = self.images_path
        self.images_path += ds.images_path
        self.original_annotations_path = self.annotations_path
        self.annotations_path += ds.annotations_path
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
        # Filter out unused classes
        annotation = [a for a in annotation if a["name"] in self.classes]
        return {"image_id": index,
                "annotations": annotation}

    def __add__(self, ds):
        """Adds the passed dataset to the current one

        Parameters
        ----------
        ds : Dataset
            Dataset to merge

        Returns
        -------
        Dataset
            self
        """
        if self.classes != ds.classes:
            raise ValueError(
                f"Operation dataset_a + dataset_b could not be computed: classes should match."
                f"Use dataset_a.extend(dataset_b, extend_classes=True) to combine both lists of classes"
            )
        self.original_images_path = self.images_path
        self.images_path += ds.images_path
        self.original_annotations_path = self.annotations_path
        self.annotations_path += ds.annotations_path
        return self

    def __getitem__(self, index: int):
        # Load images and masks
        img = load_pil_image(self.images_path[index])
        target = self._map_annotation(index)
        if self.transforms is not None:
            img, target = self.transforms(img, target)
        return img, target

    def __len__(self):
        return len(self.images_path)

    def __str__(self):
        return (f"{self.__class__.__name__}():\n"
                f"  Root: {self.dataset.local_path}\n"
                f"  Number of images: {len(self.images_path)}")


class ClassificationDataset(Dataset):
    def __init__(self, dataset, split: Path, transforms: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(dataset=dataset, split=split, transforms=transforms)
        self.classes = [e.strip() for e in open(str(self.dataset.local_path / "lists/classes_tags.txt"))]

    def _map_annotation(self, index: int):
        """See superclass for documentation"""
        with open(str(self.annotations_path[index])) as f:
            annotation = json.load(f)["annotations"]
        return {"category_id": [self.classes.index(a["name"]) for a in annotation if "tag" in a]}


class InstanceSegmentationDataset(Dataset):
    def __init__(self, dataset, split: Path, transforms: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(dataset=dataset, split=split, transforms=transforms)
        self.classes = [e.strip() for e in open(str(self.dataset.local_path / "lists/classes_masks.txt"))]
        # Prepend the default transform to convert polygons to instance masks
        if self.transforms is None:
            self.transforms = []
        self.transforms.insert(0, T.ConvertPolysToInstanceMasks())
        self.transforms = T.Compose(transforms)

    def _map_annotation(self, index: int):
        """See superclass for documentation"""
        with open(str(self.annotations_path[index])) as f:
            annotation = json.load(f)["annotations"]

        # Filter out unused classes
        annotation = [a for a in annotation if a["name"] in self.classes]

        target = []
        for obj in annotation:
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
    def __init__(self, dataset, split: Path, transforms: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(dataset=dataset, split=split, transforms=transforms)
        self.classes = [e.strip() for e in open(str(self.dataset.local_path / "lists/classes_masks.txt"))]
        if self.classes[0] == "__background__":
            self.classes = self.classes[1:]
        # Prepend the default transform to convert polygons to mask
        if self.transforms is None:
            self.transforms = []
        self.transforms.insert(0, T.ConvertPolysToMask())
        self.transforms = T.Compose(transforms)

    def _map_annotation(self, index: int):
        """See superclass for documentation"""
        with open(str(self.annotations_path[index])) as f:
            annotation = json.load(f)["annotations"]

        # Filter out unused classes
        annotation = [obj for obj in annotation if obj["name"] in self.classes]

        target = []
        for obj in annotation:
            target.append({"category_id": self.classes.index(obj["name"]),
                           "segmentation": [convert_polygon_to_sequence(obj["polygon"]["path"])]})
        return target
