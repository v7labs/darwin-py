import json
import multiprocessing as mp
from pathlib import Path
from typing import Collection, List, Optional

import numpy as np
from darwin.cli_functions import _error, _load_client
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.utils import get_classes, get_release_path, load_pil_image
from darwin.torch.transforms import (
    Compose,
    ConvertPolygonsToInstanceMasks,
    ConvertPolygonsToSemanticMask,
)
from darwin.torch.utils import polygon_area
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS, convert_polygons_to_sequences


def get_dataset(
    dataset_slug: str,
    dataset_type: str,
    partition: Optional[str] = None,
    split: str = "default",
    split_type: str = "random",
    transform: Optional[List] = None,
):
    """
    Creates and returns a dataset

    Parameters
    ----------
    dataset_slug: str
        Slug of the dataset to retrieve
    dataset_type: str
        The type of dataset [classification, instance-segmentation, semantic-segmentation]
    partition: str
        Selects one of the partitions [train, val, test, None]. (Default: None)
    split: str
        Selects the split that defines the percentages used. (Default: 'default')
    split_type: str
        Heuristic used to do the split [random, stratified]. (Default: 'random')
    transform : list[torchvision.transforms]
        List of PyTorch transforms
    """
    dataset_functions = {
        "classification": ClassificationDataset,
        "instance-segmentation": InstanceSegmentationDataset,
        "semantic-segmentation": SemanticSegmentationDataset,
    }
    dataset_function = dataset_functions.get(dataset_type)
    if not dataset_function:
        list_of_types = ", ".join(dataset_functions.keys())
        _error(f"dataset_type needs to be one of '{list_of_types}'")

    identifier = DatasetIdentifier.parse(dataset_slug)
    client = _load_client(offline=True)

    for p in client.list_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            return dataset_function(
                dataset_path=p,
                partition=partition,
                split=split,
                split_type=split_type,
                release_name=identifier.version,
                transform=transform,
            )

    _error(
        f"Dataset '{identifier.dataset_slug}' does not exist locally. "
        f"Use 'darwin dataset remote' to see all the available datasets, "
        f"and 'darwin dataset pull' to pull them."
    )


class LocalDataset(object):
    def __init__(
        self,
        dataset_path: Path,
        annotation_type: str,
        partition: Optional[str] = None,
        split: str = "default",
        split_type: str = "random",
        release_name: Optional[str] = None,
    ):
        """Creates a dataset

        Parameters
        ----------
        dataset_path: Path, str
            Path to the location of the dataset on the file system
        annotation_type: str
            The type of annotation classes [tag, bounding_box, polygon]
        partition: str
            Selects one of the partitions [train, val, test]
        split: str
            Selects the split that defines the percentages used (use 'default' to select the default split)
        split_type: str
            Heuristic used to do the split [random, stratified]
        release_name: str
            Version of the dataset
        """
        assert dataset_path is not None
        release_path = get_release_path(dataset_path, release_name)
        annotations_dir = release_path / "annotations"
        assert annotations_dir.exists()
        images_dir = dataset_path / "images"
        assert images_dir.exists()

        if partition not in ["train", "val", "test", None]:
            raise ValueError("partition should be either 'train', 'val', or 'test'")
        if split_type not in ["random", "stratified"]:
            raise ValueError("split_type should be either 'random', 'stratified'")
        if annotation_type not in ["tag", "polygon", "bounding_box"]:
            raise ValueError("annotation_type should be either 'tag', 'bounding_box', or 'polygon'")

        self.dataset_path = dataset_path
        self.annotation_type = annotation_type
        self.images_path: List[Path] = []
        self.annotations_path: List[Path] = []
        self.original_classes = None
        self.original_images_path: Optional[List[Path]] = None
        self.original_annotations_path: Optional[List[Path]] = None

        # Get the list of classes
        self.classes = get_classes(
            self.dataset_path, release_name, annotation_type=self.annotation_type, remove_background=True
        )
        self.num_classes = len(self.classes)

        # Get the list of stems
        if partition:
            # Get the split
            if split_type == "random":
                split_file = f"{split_type}_{partition}.txt"
            elif split_type == "stratified":
                split_file = f"{split_type}_{annotation_type}_{partition}.txt"
            split_path = release_path / "lists" / split / split_file
            if split_path.is_file():
                stems = (e.strip() for e in split_path.open())
            else:
                raise FileNotFoundError(
                    f"could not find a dataset partition. "
                    f"Split the dataset using `split_dataset()` from `darwin.dataset.split_manager`"
                ) from None
        else:
            # If the partition is not specified, get all the annotations
            stems = (e.relative_to(annotations_dir).parent / e.stem for e in annotations_dir.glob("**/*.json"))

        # Find all the annotations and their corresponding images
        for stem in stems:
            annotation_path = annotations_dir / f"{stem}.json"
            images = []
            for ext in SUPPORTED_IMAGE_EXTENSIONS:
                image_path = images_dir / f"{stem}{ext}"
                if image_path.exists():
                    images.append(image_path)
            if len(images) < 1:
                raise ValueError(f"Annotation ({annotation_path}) does not have a corresponding image")
            if len(images) > 1:
                raise ValueError(f"Image ({stem}) is present with multiple extensions. This is forbidden.")
            assert len(images) == 1
            self.images_path.append(images[0])
            self.annotations_path.append(annotation_path)

        if len(self.images_path) == 0:
            raise ValueError(f"Could not find any {SUPPORTED_IMAGE_EXTENSIONS} file", f" in {images_dir}")

        assert len(self.images_path) == len(self.annotations_path)

    def get_img_info(self, index: int):
        with self.annotations_path[index].open() as f:
            data = json.load(f)["image"]
            return data

    def get_height_and_width(self, index: int):
        data = self.get_img_info(index)
        return data["height"], data["width"]

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

    def get_image(self, index: int):
        return load_pil_image(self.images_path[index])

    def get_image_path(self, index: int):
        return self.images_path[index]

    def parse_json(self, index: int):
        """
        Load an annotation and filter out the extra classes according to what
        specified in `self.classes` and the annotation_type

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
            data = json.load(f)
        # Filter out unused classes and annotations of a different type
        annotations = data["annotations"]
        if self.classes is not None:
            annotations = [a for a in annotations if a["name"] in self.classes and self.annotation_type in a]
        return {
            "image_id": index,
            "image_path": str(self.images_path[index]),
            "height": data["image"]["height"],
            "width": data["image"]["width"],
            "annotations": annotations,
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

    # Loads an image with Pillow and returns the channel wise means of the image.
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

    def __getitem__(self, index: int):
        img = load_pil_image(self.images_path[index])
        target = self.parse_json(index)
        return img, target

    def __len__(self):
        return len(self.images_path)

    def __str__(self):
        return (
            f"{self.__class__.__name__}():\n"
            f"  Root: {self.dataset_path}\n"
            f"  Number of images: {len(self.images_path)}\n"
            f"  Number of classes: {len(self.classes)}"
        )


class ClassificationDataset(LocalDataset):
    def __init__(self, transform: Optional[List] = None, **kwargs):
        """
        See class `LocalDataset` for documentation
        """
        super().__init__(annotation_type="tag", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

    def __getitem__(self, index: int):
        """
        See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            image_id: int
                The index of the image in the split
            image_path: str
                The path to the image on the file system
            category_id : int
                The single label of the image selected
        """
        img = self.get_image(index)
        if self.transform is not None:
            img = self.transform(img)

        target = self.get_target(index)

        return img, target

    def get_target(self, index: int):
        """
        Returns the classification target
        """

        target = self.parse_json(index)
        annotations = target.pop("annotations")
        tags = [a["name"] for a in annotations if "tag" in a]
        if len(tags) > 1:
            raise ValueError(f"Multiple tags defined for this image ({tags}). This is not supported at the moment.")
        if len(tags) == 0:
            raise ValueError(
                f"No tags defined for this image ({self.annotations_path[index]})."
                f"This is not valid in a classification dataset."
            )
        target["category_id"] = self.classes.index(tags[0])
        target["category_name"] = tags[0]
        return target

    def get_class_idx(self, index: int):
        target = self.get_target(index)
        return target["category_id"]

    def measure_weights(self, **kwargs) -> np.ndarray:
        """
        Computes the class balancing weights (not the frequencies!!) given the train loader
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
            target = self.get_target(i)
            labels.append(target["category_id"])
        return self._compute_weights(labels)


class InstanceSegmentationDataset(LocalDataset):
    def __init__(self, transform: Optional[List] = None, **kwargs):
        """
        See `LocalDataset` class for documentation
        """
        super().__init__(annotation_type="polygon", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

        self.convert_polygons = ConvertPolygonsToInstanceMasks()

    def __getitem__(self, index: int):
        """
        Notes
        -----
        The return value is a dict with the following fields:
            image_id : int
                Index of the image inside the dataset
            image_path: str
                The path to the image on the file system
            labels : tensor(n)
                The class label of each one of the instances
            masks : tensor(n, H, W)
                Segmentation mask of each one of the instances
            boxes : tensor(n, 4)
                Coordinates of the bounding box enclosing the instances as [x, y, x, y]
            area : float
                Area in pixels of each one of the instances
        """
        img = self.get_image(index)
        target = self.get_target(index)

        img, target = self.convert_polygons(img, target)
        if self.transform is not None:
            img, target = self.transform(img, target)

        return img, target

    def get_target(self, index: int):
        """
        Returns the instance segmentation target
        """
        target = self.parse_json(index)

        annotations = []
        for annotation in target["annotations"]:
            if "polygon" not in annotation and "complex_polygon" not in annotation:
                print(f"Warning: missing polygon in annotation {self.annotations_path[index]}")
            # Extract the sequences of coordinates from the polygon annotation
            annotation_type = "polygon" if "polygon" in annotation else "complex_polygon"
            sequences = convert_polygons_to_sequences(
                annotation[annotation_type]["path"], height=target["height"], width=target["width"],
            )
            # Compute the bbox of the polygon
            x_coords = [s[0::2] for s in sequences]
            y_coords = [s[1::2] for s in sequences]
            min_x = np.min([np.min(x_coord) for x_coord in x_coords])
            min_y = np.min([np.min(y_coord) for y_coord in y_coords])
            max_x = np.max([np.max(x_coord) for x_coord in x_coords])
            max_y = np.max([np.max(y_coord) for y_coord in y_coords])
            w = max_x - min_x + 1
            h = max_y - min_y + 1
            # Compute the area of the polygon
            # TODO fix with addictive/subtractive paths in complex polygons
            poly_area = np.sum([polygon_area(x_coord, y_coord) for x_coord, y_coord in zip(x_coords, y_coords)])

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

        return target

    def measure_weights(self, **kwargs):
        """
        Computes the class balancing weights (not the frequencies!!) given the train loader
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
            target = self.get_target(i)
            labels.extend([a["category_id"] for a in target["annotations"]])
        return self._compute_weights(labels)


class SemanticSegmentationDataset(LocalDataset):
    def __init__(self, transform: Optional[List] = None, **kwargs):
        """
        See `LocalDataset` class for documentation
        """
        super().__init__(annotation_type="polygon", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

        self.convert_polygons = ConvertPolygonsToSemanticMask()

    def __getitem__(self, index: int):
        """
        See superclass for documentation

        Notes
        -----
        The return value is a dict with the following fields:
            image_id : int
                Index of the image inside the dataset
            image_path: str
                The path to the image on the file system
            mask : tensor(H, W)
                Segmentation mask where each pixel encodes a class label
        """
        img = self.get_image(index)
        target = self.get_target(index)

        img, target = self.convert_polygons(img, target)
        if self.transform is not None:
            img, target = self.transform(img, target)

        return img, target

    def get_target(self, index: int):
        """
        Returns the semantic segmentation target
        """
        target = self.parse_json(index)

        annotations = []
        for obj in target["annotations"]:
            sequences = convert_polygons_to_sequences(
                obj["polygon"]["path"], height=target["height"], width=target["width"],
            )
            # Discard polygons with less than three points
            sequences[:] = [s for s in sequences if len(s) >= 6]
            if not sequences:
                continue
            annotations.append({"category_id": self.classes.index(obj["name"]), "segmentation": sequences})
        target["annotations"] = annotations

        return target

    def measure_weights(self, **kwargs):
        """
        Computes the class balancing weights (not the frequencies!!) given the train loader
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
            target = self.get_target(i)
            labels.extend([a["category_id"] for a in target["annotations"]])
        return self._compute_weights(labels)
