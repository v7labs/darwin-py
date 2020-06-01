import multiprocessing as mp
from pathlib import Path
from typing import Collection, List, Optional, Union

import numpy as np

from darwin.dataset import LocalDataset
from darwin.torch.transforms import Compose, ConvertPolygonsToInstanceMasks, ConvertPolygonsToSegmentationMask
from darwin.torch.utils import convert_polygons_to_sequences, load_pil_image, polygon_area


def get_dataset(
    dataset_path: Union[Path, str],
    dataset_type: str,
    partition: Optional[str] = None,
    split: str = "default",
    split_type: str = "random",
    release_name: Optional[str] = None,
    transform: Optional[List] = None,
):
    """ Creates and returns a dataset

    Parameters
    ----------
    dataset_path: Path, str
        Path to the location of the dataset on the file system
    dataset_type: str
        The type of dataset [classification, instance_segmentation, semantic_segmentation]
    partition: str
        Selects one of the partitions [train, val, test]
    split: str
        Selects the split that defines the percentages used (use 'default' to select the default split)
    split_type: str
        Heuristic used to do the split [random, stratified]
    release_name: str
        Version of the dataset
    transform : list[torchvision.transforms]
        List of PyTorch transforms
    """
    dataset_functions = {
        "classification": ClassificationDataset,
        "instance_segmentation": InstanceSegmentationDataset,
        "semantic_segmentation": SemanticSegmentationDataset,
    }
    dataset_function = dataset_functions.get(dataset_type)
    if not dataset_function:
        list_of_types = ", ".join(dataset_functions.keys())
        raise ValueError(f"dataset_type needs to be one of '{list_of_types}'")

    if isinstance(dataset_path, str):
        dataset_path = Path(dataset_path)

    return dataset_function(
        dataset_path=dataset_path,
        partition=partition,
        split=split,
        split_type=split_type,
        release_name=release_name,
        transform=transform,
    )


class DarwinDataset(LocalDataset):
    def measure_mean_std(self, multi_threaded: bool = True):
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
                mean = np.sum(np.array(results), axis=0) / len(self.images_path)
                # Online image_classification deviation
                results = pool.starmap(self._return_std, [[item, mean] for item in self.images_path])
                std_sum = np.sum(np.array([item[0] for item in results]), axis=0)
                total_pixel_count = np.sum(np.array([item[1] for item in results]))
                std = np.sqrt(std_sum / total_pixel_count)
                # Shut down the pool
                pool.close()
                pool.join()
            return mean, std
        else:
            # Online mean
            results = [self._return_mean(f) for f in self.images_path]
            mean = np.sum(np.array(results), axis=0) / len(self.images_path)
            # Online image_classification deviation
            results = [self._return_std(f, mean) for f in self.images_path]
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
    def _compute_weights(labels: Collection):
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
        m2 = np.square(np.array([img[:, :, 0] - mean[0], img[:, :, 1] - mean[1], img[:, :, 2] - mean[2]]))
        return np.sum(np.sum(m2, axis=1), 1), m2.size / 3.0


class ClassificationDataset(DarwinDataset):
    def __init__(
        self, transform: Optional[List] = None, **kwargs,
    ):
        """See class `LocalDataset` for documentation"""
        super().__init__(annotation_type="tag", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

    def __getitem__(self, index: int):
        """See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            image_id: int
                The index of the image in the split
            original_filename: str
                The path to the image on the file system
            category_id : int
                The single label of the image selected.
        """
        img = load_pil_image(self.images_path[index])
        if self.transform is not None:
            img = self.transform(img)

        target = self.parse_json(index)
        annotations = target.pop("annotations")
        tags = [self.classes.index(a["name"]) for a in annotations if "tag" in a]
        if len(tags) > 1:
            raise ValueError(
                f"Multiple tags defined for this image ({tags}). " f"This is not valid in a classification dataset."
            )
        if len(tags) == 0:
            raise ValueError(
                f"No tags defined for this image ({self.annotations_path[index]})."
                f"This is not valid in a classification dataset."
            )
        target["category_id"] = tags[0]

        return img, target

    def measure_weights(self, **kwargs) -> np.ndarray:
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
        for i, _filename in enumerate(self.images_path):
            target = self._map_annotation(i)
            labels.append(target["category_id"])
        return self._compute_weights(labels)


class InstanceSegmentationDataset(DarwinDataset):
    def __init__(
        self, transform: Optional[List] = None, convert_polygons_to_masks: Optional[bool] = True, **kwargs,
    ):
        """See `LocalDataset` class for documentation"""
        super().__init__(annotation_type="polygon", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

        self.convert_polygons = ConvertPolygonsToInstanceMasks() if convert_polygons_to_masks else None

    def __getitem__(self, index: int):
        """

        Notes
        -----
        The return value is a dict with the following fields:
            image_id : int
                Index of the image inside the dataset
            original_filename: str
                The path to the image on the file system
            annotations : list[Dict]
                List of annotations, where each annotation is a dict with:
                category_id : int
                    The single label of the image selected.
                segmentation : ndarray(1,)
                    Array of points [x,y,x,y,x,y ...] composing the polygon enclosing the object
                bbox : ndarray(1,)
                    Coordinates of the bounding box enclosing the instance as [x, y, w, h]
                area : float
                    Area of the polygon
        """
        img = load_pil_image(self.images_path[index])
        target = self.parse_json(index)

        annotations = []
        for annotation in target["annotations"]:
            assert "name" in annotation
            assert "polygon" in annotation
            # Extract the sequences of coordinates from the polygon annotation
            sequences = convert_polygons_to_sequences(annotation["polygon"]["path"])
            # Discard polygons with less than three points
            sequences[:] = [s for s in sequences if len(s) >= 6]
            if not sequences:
                continue
            # Compute the bbox of the polygon
            x_coords = [s[0::2] for s in sequences]
            y_coords = [s[1::2] for s in sequences]
            min_x = np.min([np.min(x_coord) for x_coord in x_coords])
            min_y = np.min([np.min(y_coord) for y_coord in y_coords])
            max_x = np.max([np.max(x_coord) for x_coord in x_coords])
            max_y = np.max([np.max(y_coord) for y_coord in y_coords])
            w = max_x - min_x + 1
            h = max_y - min_y + 1
            bbox_area = w * h
            # Compute the area of the polygon
            poly_area = np.sum([polygon_area(x_coord, y_coord) for x_coord, y_coord in zip(x_coords, y_coords)])
            assert poly_area <= bbox_area

            # Create and append the new entry for this annotation
            annotations.append(
                {
                    "category_id": self.classes.index(annotation["name"]),
                    "segmentation": sequences,
                    "bbox": [min_x, min_y, w, h],
                    "area": poly_area,
                }
            )
        target["annotations"] = annotations

        if self.convert_polygons is not None:
            img, target = self.convert_polygons(img, target)
        if self.transform is not None:
            img, target = self.transform(img, target)

        return img, target

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
            labels.extend([a["category_id"] for a in target["annotations"]])
        return self._compute_weights(labels)


class SemanticSegmentationDataset(DarwinDataset):
    def __init__(
        self, transform: Optional[List] = None, convert_polygons_to_masks: Optional[bool] = True, **kwargs,
    ):
        """See `LocalDataset` class for documentation"""
        super().__init__(annotation_type="polygon", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

        self.convert_polygons = ConvertPolygonsToSegmentationMask() if convert_polygons_to_masks else None

    def __getitem__(self, index: int):
        """See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            image_id : int
                Index of the image inside the dataset
            original_filename: str
                The path to the image on the file system
            annotations : list
                List of annotations, where each annotation is a dict with:
                category_id : TODO complete documentation
                segmentation :
        """
        img = load_pil_image(self.images_path[index])
        target = self.parse_json(index)

        annotations = []
        for obj in target["annotations"]:
            sequences = convert_polygons_to_sequences(obj["polygon"]["path"])
            # Discard polygons with less than three points
            sequences[:] = [s for s in sequences if len(s) >= 6]
            if not sequences:
                continue
            annotations.append(
                {"category_id": self.classes.index(obj["name"]), "segmentation": np.array(sequences),}
            )
        target["annotations"] = annotations

        if self.convert_polygons is not None:
            img, target = self.convert_polygons(img, target)
        if self.transform is not None:
            img, target = self.transform(img, target)

        return img, target

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
            labels.extend([a["category_id"] for a in target["annotations"]])
        return self._compute_weights(labels)
