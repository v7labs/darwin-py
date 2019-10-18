import json
from pathlib import Path
from typing import List, Optional

import numpy as np

import darwin.torch.transforms as T
import torch.utils.data as data
from darwin.torch.utils import (
    convert_polygon_to_sequence,
    load_pil_image,
    polygon_area,
)

class Dataset(data.Dataset):
    def __init__(self, root: Path, split: Path, transforms: Optional[List] = None):
        """ Creates a dataset

        Parameters
        ----------
        root : Path
            Path to the location of the dataset on the file system
        split : Path
            Path to the *.txt file containing the list of files for this split.
        transforms : list[torchvision.transforms]
            List of PyTorch transforms
        """
        self.root = root
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
                                    f" in {self.root}.")
        extensions = ["jpg", "jpeg", "png"]
        stems = (e.strip() for e in split.open())
        for stem in stems:
            annotation_path = self.root / f"annotations/{stem}.json"
            images = [image for image in self.root.glob(f"images/{stem}.*") if image.suffix in extensions]
            if len(images) < 1:
                raise ValueError(f"Annotation ({annotation_path}) does"
                                 f" not have a corresponding image")
            if len(images) > 1:
                raise ValueError(f"Image ({stem}) is present with multiple extensions."
                                 f" This is forbidden.")
            assert len(images) == 1
            image_path = images[0]
            self.images_path.append(image_path)
            self.annotations_path.append(annotation_path)

        if len(self.images_path) == 0:
            raise ValueError(f"Could not find any {extensions} file"
                             f" in {self.root / 'images'}")

        assert len(self.images_path) == len(self.annotations_path)

    def extend(self, dataset, extend_classes: bool = False):
        """Extends the current dataset with another one

        Parameters
        ----------
        dataset : Dataset
            Dataset to merge
        extend_classes : bool
            Extend the current set of classes by merging with the passed dataset ones

        Returns
        -------
        Dataset
            self
        """
        if self.classes != dataset.classes and not extend_classes:
            raise ValueError(f"Operation dataset_a + dataset_b could not be computed: classes "
                             f"should match. Use flag extend_classes=True to combine both lists "
                             f"of classes.")
        self.classes = list(set(self.classes).union(set(dataset.classes)))

        self.original_images_path = self.images_path
        self.images_path += dataset.images_path
        self.original_annotations_path = self.annotations_path
        self.annotations_path += dataset.annotations_path
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
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]
        # Filter out unused classes
        annotation = [a for a in annotation if a["name"] in self.classes]
        return {"image_id": index,
                "annotations": annotation}

    def measure_mean_std(self, **kwargs):
        """Computes mean and std of train images, given the train loader

        Returns
        -------
        mean : ndarray[double]
            Mean value (for each channel) of all pixels of the images in the input folder
        std : ndarray[double]
            Standard deviation (for each channel) of all pixels of the images in the input folder
        """
        raise NotImplementedError

    def measure_weights(self, **kwargs):
        """Computes the class balancing weights (not the frequencies!!) given the train loader

        Returns
        -------
        class_weights : ndarray[double]
            Weight for each class in the train set (one for each class)
        """
        raise NotImplementedError

    def __add__(self, dataset):
        """Adds the passed dataset to the current one

        Parameters
        ----------
        dataset : Dataset
            Dataset to merge

        Returns
        -------
        Dataset
            self
        """
        if self.classes != dataset.classes:
            raise ValueError(
                f"Operation dataset_a + dataset_b could not be computed: classes should match."
                f"Use dataset_a.extend(dataset_b, extend_classes=True) to combine both lists of classes"
            )
        self.original_images_path = self.images_path
        self.images_path += dataset.images_path
        self.original_annotations_path = self.annotations_path
        self.annotations_path += dataset.annotations_path
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
                f"  Root: {self.root}\n"
                f"  Number of images: {len(self.images_path)}")


class ClassificationDataset(Dataset):
    def __init__(self, root, split: Path, transforms: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(root=root, split=split, transforms=transforms)
        self.classes = [e.strip() for e in open(str(self.root / "lists/classes_tags.txt"))]

    def _map_annotation(self, index: int):
        """See superclass for documentation"""
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]
        return {"category_id": [self.classes.index(a["name"]) for a in annotation if "tag" in a]}


class InstanceSegmentationDataset(Dataset):
    def __init__(self, root, split: Path, transforms: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(root=root, split=split, transforms=transforms)
        self.classes = [e.strip() for e in open(str(self.root / "lists/classes_masks.txt"))]
        # Prepend the default transform to convert polygons to instance masks
        if self.transforms is None:
            self.transforms = []
        self.transforms.insert(0, T.ConvertPolysToInstanceMasks())
        self.transforms = T.Compose(transforms)

    def _map_annotation(self, index: int):
        """See superclass for documentation"""
        with self.annotations_path[index].open() as f:
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
    def __init__(self, root, split: Path, transforms: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(root=root, split=split, transforms=transforms)
        self.classes = [e.strip() for e in open(str(self.root / "lists/classes_masks.txt"))]
        if self.classes[0] == "__background__":
            self.classes = self.classes[1:]
        # Prepend the default transform to convert polygons to mask
        if self.transforms is None:
            self.transforms = []
        self.transforms.insert(0, T.ConvertPolysToMask())
        self.transforms = T.Compose(transforms)

    def _map_annotation(self, index: int):
        """See superclass for documentation"""
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]

        # Filter out unused classes
        annotation = [obj for obj in annotation if obj["name"] in self.classes]

        target = []
        for obj in annotation:
            target.append({"category_id": self.classes.index(obj["name"]),
                           "segmentation": [convert_polygon_to_sequence(obj["polygon"]["path"])]})
        return target
