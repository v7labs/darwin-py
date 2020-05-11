import json
import multiprocessing as mp
from pathlib import Path
from typing import Callable, Collection, List, Optional

import numpy as np
import torch.utils.data as data

from darwin.torch.transforms import Compose, ConvertPolygonsToInstanceMasks, ConvertPolygonToMask
from darwin.torch.utils import convert_polygons_to_sequences, load_pil_image, polygon_area
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS, is_image_extension_allowed
from darwin.dataset.utils import get_classes, get_release_path


def get_dataset(
    dataset_path: Path,
    dataset_type: str,
    partition: Optional[str] = None,
    split: Optional[str] = None,
    split_type: Optional[str] = None,
    release_name: Optional[str] = None,
    transform: Optional[List] = None
):
    """ Creates and returns a dataset

    Parameters
    ----------
    dataset_path
        Path to the location of the dataset on the file system
    dataset_type
        The type of dataset [classification, instances_segmentation, semantic_segmentation]
    partition
        Selects one of the partitions [train, val, test]
    split
        Selects the split that defines the percetages used (use 'split' to select the default split)
    split_type
        Heuristic used to do the split [random, stratified, None]
    release_name: str
        Version of the dataset
    transform : list[torchvision.transforms]
        List of PyTorch transforms
    """
    assert dataset_type in ["classification", "instance_segmentation", "semantic_sgmentation"]
    dataset_functions = {
        "classification": ClassificationDataset,
        "instance_segmentation": InstanceSegmentationDataset,
        "semantic_segmentation": SemanticSegmentationDataset,
    }
    dataset_function = dataset_functions[dataset_type]

    return dataset_function(
        dataset_path=dataset_path,
        partition=partition,
        split=split,
        split_type=split_type,
        release_name=release_name,
        transform=transform,
    )


class Dataset(data.Dataset):
    def __init__(
        self,
        dataset_path: Path,
        annotation_type: str,
        partition: Optional[str] = None,
        split: Optional[str] = None,
        split_type: Optional[str] = None,
        release_name: Optional[str] = None,
        transform: Optional[List] = None
    ):
        """ Creates a dataset

        Parameters
        ----------
        dataset_path
            Path to the location of the dataset on the file system
        annotation_type
            The type of annotation classes [tag, box, polygon]
        partition
            Selects one of the partitions [train, val, test]
        split
            Selects the split that defines the percetages used (use 'split' to select the default split)
        split_type
            Heuristic used to do the split [random, stratified, None]
        release_name: str
            Version of the dataset
        transform : list[torchvision.transforms]
            List of PyTorch transforms
        """
        assert dataset_path is not None
        release_path = get_release_path(dataset_path, release_name)
        annotations_dir = release_path / "annotations"
        assert annotations_dir.exists()
        images_dir = dataset_path / "images"
        assert images_dir.exists()

        if partition not in ["train", "val", "test", None]:
            raise ValueError("partition should be either 'train', 'val', or 'test'")
        if split_type not in ["random", "stratified", None]:
            raise ValueError("split_type should be either 'random', 'stratified'")
        if annotation_type not in ["tag", "polygon", "box"]:
            raise ValueError("annotation_type should be either 'tag', 'box', or 'polygon'")

        self.dataset_path = dataset_path
        self.transform = transform
        self.images_path: List[Path] = []
        self.annotations_path: List[Path] = []
        self.original_classes = None
        self.original_images_path: Optional[List[Path]] = None
        self.original_annotations_path: Optional[List[Path]] = None
        self.convert_polygons: Optional[Callable] = None

        # Compose the transform if necessary
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(transform)

        # Get the list of classes
        self.classes = get_classes(
            self.dataset_path,
            self.release_name,
            annotation_type=self.annotation_type,
            remove_background=True
        )

        # Get the list of stems
        if split:
            # Get the split
            if split_type is None:
                split_file = f"{partition}.txt"
            elif split_type == "random":
                split_file = f"{split_type}_{partition}.txt"
            elif split_type == "stratified":
                split_file = f"{split_type}_{annotation_type}_{partition}.txt"
            split_path = release_path / "lists" / split / split_file
            stems = (e.strip() for e in split_path.open())
        else:
            # If the split is not specified, get all the annotations
            stems = [e.stem for e in annotations_dir.glob("*.json")]

        images_paths = []
        annotations_paths = []

        # Find all the annotations and their corresponding images
        for stem in stems:
            annotation_path = annotations_dir / f"{stem}.json"
            images = []
            for ext in SUPPORTED_IMAGE_EXTENSIONS:
                image_path = images_dir / f"{stem}{ext}"
                if image_path.exists():
                    images.append(image_path)
            if len(images) < 1:
                raise ValueError(
                    f"Annotation ({annotation_path}) does not have a corresponding image"
                )
            if len(images) > 1:
                raise ValueError(
                    f"Image ({stem}) is present with multiple extensions. This is forbidden."
                )
            assert len(images) == 1
            self.images_paths.append(images[0])
            self.annotations_paths.append(annotation_path)

        if len(self.images_paths) == 0:
            raise ValueError(
                f"Could not find any {SUPPORTED_IMAGE_EXTENSIONS} file" f" in {dataset_path / 'images'}"
            )

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
        if self.annotation_type != dataset.annotation_type:
            raise ValueError("Annotation type of both datasets should match")
        if self.classes != dataset.classes and not extend_classes:
            raise ValueError(
                f"Operation dataset_a + dataset_b could not be computed: classes "
                f"should match. Use flag extend_classes=True to combine both lists "
                f"of classes."
            )
        self.classes = list(set(self.classes).union(set(dataset.classes)))

        self.original_images_path = self.images_path
        self.images_path += dataset.images_path
        self.original_annotations_path = self.annotations_path
        self.annotations_path += dataset.annotations_path
        return self

    def get_img_info(self, index: int):
        with self.annotations_path[index].open() as f:
            data = json.load(f)["image"]
            return data

    def get_height_and_width(self, index: int):
        data = self.get_img_info(index)
        return data["height"], data["width"]

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

        Notes
        -----
        The return value is a dict with the following fields:
            image_id: int
                The index of the image in the split
            original_filename: str
                The path to the image on the file system
            annotations : str
                The original raw annotation
        """
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]
        # Filter out unused classes
        if self.classes is not None:
            annotation = [a for a in annotation if a["name"] in self.classes]
        return {
            "image_id": index,
            "original_filename": self.images_path[index],
            "annotations": annotation,
        }

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
                results = pool.starmap(
                    self._return_std, [[item, mean] for item in self.images_path]
                )
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
        m2 = np.square(
            np.array([img[:, :, 0] - mean[0], img[:, :, 1] - mean[1], img[:, :, 2] - mean[2]])
        )
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
        if self.annotation_type != dataset.annotation_type:
            raise ValueError("Annotation type of both datasets should match")
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
        return (
            f"{self.__class__.__name__}():\n"
            f"  Root: {self.root}\n"
            f"  Number of images: {len(self.images_path)}"
        )


####################################################################################################


class ClassificationDataset(Dataset):
    def __init__(self, **kwargs):
        """See superclass for documentation"""
        super().__init__(annotation_type="tag", **kwargs)

    def _map_annotation(self, index: int):
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
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]
            tags = [self.classes.index(a["name"]) for a in annotation if "tag" in a]
            if len(tags) > 1:
                raise ValueError(
                    f"Multiple tags defined for this image ({tags}). "
                    f"This is not valid in a classification dataset."
                )
            if len(tags) == 0:
                raise ValueError(
                    f"No tags defined for this image ({self.annotations_path[index]})."
                    f"This is not valid in a classification dataset."
                )
        return {
            "image_id": index,
            "original_filename": self.images_path[index],
            "category_id": tags[0],
        }

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


####################################################################################################


class InstanceSegmentationDataset(Dataset):
    def __init__(
        self,
        convert_polygons_to_masks: Optional[bool] = True,
        **kwargs,
    ):
        """See superclass for documentation"""
        super().__init__(annotation_type="polygon", **kwargs)
        self.convert_polygons = (
            ConvertPolygonsToInstanceMasks() if convert_polygons_to_masks else None
        )

    def _map_annotation(self, index: int):
        """See superclass for documentation

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
        with self.annotations_path[index].open() as f:
            annotations = json.load(f)["annotations"]

        # Filter out unused classes
        if self.classes is not None:
            annotations = [a for a in annotations if a["name"] in self.classes]

        target = []
        for annotation in annotations:
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
            poly_area = np.sum(
                [polygon_area(x_coord, y_coord) for x_coord, y_coord in zip(x_coords, y_coords)]
            )
            assert poly_area <= bbox_area

            # Create and append the new entry for this annotation
            target.append(
                {
                    "category_id": self.classes.index(annotation["name"]),
                    "segmentation": sequences,
                    "bbox": [min_x, min_y, w, h],
                    "area": poly_area,
                }
            )

        return {
            "image_id": index,
            "original_filename": self.images_path[index],
            "annotations": target,
        }

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


####################################################################################################


class SemanticSegmentationDataset(Dataset):
    def __init__(
        self,
        convert_polygons_to_masks: Optional[bool] = True,
        **kwargs,
    ):
        """See superclass for documentation"""
        super().__init__(annotation_type="polygon", **kwargs)
        self.convert_polygons = (
            ConvertPolygonsToInstanceMasks() if convert_polygons_to_masks else None
        )

    def _map_annotation(self, index: int):
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
        with self.annotations_path[index].open() as f:
            annotation = json.load(f)["annotations"]

        # Filter out unused classes
        if self.classes is not None:
            annotation = [obj for obj in annotation if obj["name"] in self.classes]

        target = []
        for obj in annotation:
            sequences = convert_polygons_to_sequences(obj["polygon"]["path"])
            # Discard polygons with less than three points
            sequences[:] = [s for s in sequences if len(s) >= 6]
            if not sequences:
                continue
            target.append(
                {
                    "category_id": self.classes.index(obj["name"]),
                    "segmentation": np.array(sequences),
                }
            )
        return {
            "image_id": index,
            "original_filename": self.images_path[index],
            "annotations": target,
        }

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
