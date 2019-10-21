import json
import multiprocessing as mp
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch.utils.data as data

import darwin.torch.transforms as T
from darwin.torch.utils import (
    convert_polygon_to_sequence,
    load_pil_image,
    polygon_area,
)

####################################################################################################
# Dataset
class Dataset(data.Dataset):
    def __init__(self, root: Path, split: Path, transform: Optional[List] = None):
        """ Creates a dataset

        Parameters
        ----------
        root : Path
            Path to the location of the dataset on the file system
        split : Path
            Path to the *.txt file containing the list of files for this split.
        transform : list[torchvision.transforms]
            List of PyTorch transforms
        """
        self.root = root
        self.split = split
        self.transform = transform
        self.images_path = []
        self.annotations_path = []
        self.classes = None
        self.original_classes = None
        self.original_images_path = None
        self.original_annotations_path = None
        self.convert_polygons = None

        #Compose the transform if necessary
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = T.Compose(transform)

        # Populate internal lists of annotations and images paths
        if not self.split.exists():
            raise FileNotFoundError(f"Could not find partition {self.split}"
                                    f" in {self.root}.")
        extensions = [".jpg", ".jpeg", ".png"]
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

    def measure_mean_std(self, multi_threaded: Optional[bool] = True, **kwargs):
        """Computes mean and std of train images, given the train loader

        Parameters
        ----------
        multi_threaded : bool
            Uses multiprocessing to download the dataset in parallel.

        Returns
        -------
        mean : ndarray[double]
            Mean value (for each channel) of all pixels of the images in the input folder
        std : ndarray[double]
            Standard deviation (for each channel) of all pixels of the images in the input folder
        """
        if multi_threaded:
            # Set up a pool of workers
            with mp.Pool(mp.cpu_count()) as pool:
                # Online mean
                results = pool.map(self._return_mean, self.images_path)
                mean = np.sum(np.array(results), axis=0)  / len(self.images_path)
                # Online image_classification deviation
                results = pool.starmap(self._return_std, [[item, mean] for item in  self.images_path])
                std_sum = np.sum(np.array([item[0] for item in results]), axis=0)
                total_pixel_count = np.sum(np.array([item[1] for item in results]))
                std = np.sqrt(std_sum / total_pixel_count)
                # Shut down the pool
                pool.close()
                pool.join()
            return mean, std
        else:
            # Online mean
            results = [self._return_mean(f) for f in  self.images_path]
            mean = np.sum(np.array(results), axis=0) / len(self.images_path)
            # Online image_classification deviation
            results = [self._return_std(f, mean) for f in  self.images_path]
            std_sum = np.sum(np.array([item[0] for item in results]), axis=0)
            total_pixel_count = np.sum(np.array([item[1] for item in results]))
            std = np.sqrt(std_sum / total_pixel_count)
            return mean, std

    def measure_weights(self, **kwargs):
        """Computes the class balancing weights (not the frequencies!!) given the train loader

        Returns
        -------
        class_weights : ndarray[double]
            Weight for each class in the train set (one for each class)
        """
        raise NotImplementedError("Base class Dataset does not have an implementation for this")

    @staticmethod
    def _compute_weights(labels: np.ndarray):
        """Given an array of labels computes the weights normalized

        Parameters
        ----------
        labels : ndarray[int]
            Array of labels

        Returns
        -------
        ndarray[float]
            Array of weights (one for each unique class) which are the inverse of their frequency
        """
        class_support = np.unique(labels, return_counts=True)[1]
        class_frequencies = class_support / len(labels)
        # Class weights are the inverse of the class frequencies
        class_weights = 1 / class_frequencies
        # Normalize vector to sum up to 1.0 (in case the Loss function does not do it)
        class_weights /= class_weights.sum()
        return class_weights

    # Loads an image with OpenCV and returns the channel wise means of the image.
    @staticmethod
    def _return_mean(image_path):
        img = np.array(load_pil_image(image_path))
        mean = np.array([np.mean(img[:, :, 0]), np.mean(img[:, :, 1]), np.mean(img[:, :, 2])])
        return mean / 255.0

    # Loads an image with OpenCV and returns the channel wise std of the image.
    @staticmethod
    def _return_std(image_path, mean):
        img = np.array(load_pil_image(image_path)) / 255.0
        m2 = np.square(np.array(
            [img[:, :, 0] - mean[0], img[:, :, 1] - mean[1], img[:, :, 2] - mean[2]]
        ))
        return np.sum(np.sum(m2, axis=1), 1), m2.size / 3.0

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
        if self.convert_polygons is not None:
            img, target = self.convert_polygons(img, target)
        if self.transform is not None:
            img, target = self.transform(img, target)
        return img, target

    def __len__(self):
        return len(self.images_path)

    def __str__(self):
        return (f"{self.__class__.__name__}():\n"
                f"  Root: {self.root}\n"
                f"  Number of images: {len(self.images_path)}")


####################################################################################################
# ClassificationDataset
class ClassificationDataset(Dataset):
    def __init__(self, root, split: Path, transform: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(root=root, split=split, transform=transform)
        self.classes = [e.strip() for e in open(str(self.root / "lists/classes_tag.txt"))]

    def _map_annotation(self, index: int):
        """See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            category_id : int
                The single label of the image selected.
        """
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]
            tags = [self.classes.index(a["name"]) for a in annotation if "tag" in a]
            if len(tags) > 1:
                raise ValueError(f"Multiple tags defined for this image ({tags}). "
                                 f"This is not valid in a classification dataset.")
            if len(tags) == 0:
                raise ValueError(f"No tags defined for this image ({self.annotations_path[index]})."
                                 f"This is not valid in a classification dataset.")
        return {"category_id": tags[0]}

    def measure_weights(self, **kwargs):
        """Computes the class balancing weights (not the frequencies!!) given the train loader
        Get the weights proportional to the inverse of their class frequencies.
        The vector sums up to 1

        Returns
        -------
        class_weights : ndarray[double]
            Weight for each class in the train set (one for each class) as a 1D array normalized
        """
        # Collect all the labels by iterating over the whole dataset
        labels = []
        for i, filename in enumerate(self.images_path):
            target = self._map_annotation(i)
            labels.append(target['category_id'])
        return self.compute_weights(labels)


####################################################################################################
# InstanceSegmentationDataset
class InstanceSegmentationDataset(Dataset):
    def __init__(self, root, split: Path, transform: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(root=root, split=split, transform=transform)
        self.classes = [e.strip() for e in open(str(self.root / "lists/classes_polygon.txt"))]
        self.convert_polygons = T.ConvertPolygonsToInstanceMasks()

    def _map_annotation(self, index: int):
        """See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            image_id : int
                Index of the image inside the dataset
            annotations : list[Dict]
                List of annotations, where each annotation is a dict with:
                iscrowd : int
                    Flag to denote where the annotation more than one instance (can be 0 or 1)
                category_id : int
                    The single label of the image selected.
                segmentation : ndarray(1,)
                    Array of points [x,y,x,y,x,y ...] composing the polygon enclosing the object
                bbox : ndarray(1,)
                    Coordinates of the bounding box enclosing the instance as [x, y, w, h]
                area : float
                    Area of the polygon
        """
        with self.annotations_path[index].open() as f:
            annotations = json.load(f)["annotations"]

        # Filter out unused classes
        annotations = [a for a in annotations if a["name"] in self.classes]

        target = []
        for annotation in annotations:
            assert "name" in annotation
            assert "polygon" in annotation
            # Extract the sequence of coordinates from the polygon annotation
            sequence = convert_polygon_to_sequence(annotation["polygon"]["path"])
            # Compute the bbox of the polygon
            x_coords = sequence[0::2]
            y_coords = sequence[1::2]
            x = np.max((0, np.min(x_coords) - 1))
            y = np.max((0, np.min(y_coords) - 1))
            w = (np.max(x_coords) - x) + 1
            h = (np.max(y_coords) - y) + 1
            # Compute the area of the polygon
            poly_area = polygon_area(x_coords, y_coords)
            bbox_area = w * h
            if poly_area > bbox_area:
                raise ValueError(
                    f"polygon's area should be <= bbox's area. Failed {poly_area} <= {bbox_area}"
                )
            # Create and append the new entry for this annotation
            target.append({
                "iscrowd": 0,
                "category_id": self.classes.index(annotation["name"]),
                "segmentation": [sequence],  # List type is used for backward compatibility
                "bbox": [x, y, w, h],
                "area": poly_area,
            })

        return {'image_id': index,
                'annotations': target}

    def measure_weights(self, **kwargs):
        """Computes the class balancing weights (not the frequencies!!) given the train loader
        Get the weights proportional to the inverse of their class frequencies.
        The vector sums up to 1

        Returns
        -------
        class_weights : ndarray[double]
            Weight for each class in the train set (one for each class) as a 1D array normalized
        """
        # Collect all the labels by iterating over the whole dataset
        labels = []
        for i, _ in enumerate(self.images_path):
            target = self._map_annotation(i)
            labels.append([a['category_id'] for a in target['annotations']])
        return self.compute_weights(labels)

####################################################################################################
# SemanticSegmentationDataset
class SemanticSegmentationDataset(Dataset):
    def __init__(self, root, split: Path, transform: Optional[List] = None):
        """See superclass for documentation"""
        super().__init__(root=root, split=split, transform=transform)
        self.classes = [e.strip() for e in open(str(self.root / "lists/classes_polygon.txt"))]
        if self.classes[0] == "__background__":
            self.classes = self.classes[1:]
        self.convert_polygons = T.ConvertPolygonToMask()

    def _map_annotation(self, index: int):
        """See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            TODO complete documentation
            image_id :
            annotations : list
                List of annotations, where each annotation is a dict with:
                category_id :
                segmentation :
        """
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]

        # Filter out unused classes
        annotation = [obj for obj in annotation if obj["name"] in self.classes]

        target = []
        for obj in annotation:
            target.append({"category_id": self.classes.index(obj["name"]),
                           "segmentation": np.array([convert_polygon_to_sequence(obj["polygon"]["path"])])})
        return {'image_id': index,
                'annotations': target}

    def measure_weights(self, **kwargs):
        """Computes the class balancing weights (not the frequencies!!) given the train loader
        Get the weights proportional to the inverse of their class frequencies.
        The vector sums up to 1

        Returns
        -------
        class_weights : ndarray[double]
            Weight for each class in the train set (one for each class) as a 1D array normalized
        """
        # Collect all the labels by iterating over the whole dataset
        labels = []
        for i, _ in enumerate(self.images_path):
            target = self._map_annotation(i)
            labels.extend([a['category_id'] for a in target['annotations']])
        return self.compute_weights(labels)