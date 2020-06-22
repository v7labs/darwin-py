import json
import multiprocessing as mp
from pathlib import Path
from typing import Collection, List, Optional

import numpy as np

from darwin.dataset.utils import get_classes, get_release_path, load_pil_image
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS


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
        """ Creates a dataset

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
                    f"Split the dataset using `split_dataset()` from `darwin.dataset.utils`"
                ) from None
        else:
            # If the partition is not specified, get all the annotations
            stems = [e.stem for e in annotations_dir.glob("*.json")]

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
