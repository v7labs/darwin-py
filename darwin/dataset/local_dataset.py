import multiprocessing as mp
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import orjson as json
from PIL import Image as PILImage

from darwin.dataset.utils import get_classes, get_release_path, load_pil_image
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS, parse_darwin_json


class LocalDataset(object):
    """
    Base class representing a V7 Darwin dataset that has been pulled locally already.
    It can be used with PyTorch dataloaders. See ``darwin.torch`` module for more specialized dataset classes, extending this one.

    Parameters
    ----------
    dataset_path : Path
        Path to the location of the dataset on the file system.
    annotation_type : str
        The type of annotation classes ``["tag", "bounding_box", "polygon"]``.
    partition : Optional[str], default: None
        Selects one of the partitions ``["train", "val", "test"]``.
    split : str, default: "default"
        Selects the split that defines the percentages used (use 'default' to select the default split).
    split_type : str, default: "random"
        Heuristic used to do the split ``["random", "stratified"]``.
    release_name : Optional[str], default: None
        Version of the dataset.

    Attributes
    ----------
    dataset_path : Path
        Path to the location of the dataset on the file system.
    annotation_type : str
        The type of annotation classes ``["tag", "bounding_box", "polygon"]``.
    partition : Optional[str], default: None
        Selects one of the partitions ``["train", "val", "test"]``.
    split : str, default: "default"
        Selects the split that defines the percentages used (use 'default' to select the default split).
    split_type : str, default: "random"
        Heuristic used to do the split ``["random", "stratified"]``.
    release_name : Optional[str], default: None
        Version of the dataset.

    Raises
    ------
    ValueError

        - If ``partition``, ``split_type`` or ``annotation_type`` have an invalid value.
        - If an annotation has no corresponding image
        - If an image has multiple extensions (meaning it is present in multiple formats)
        - If no images are found
    """

    def __init__(
        self,
        dataset_path: Path,
        annotation_type: str,
        partition: Optional[str] = None,
        split: str = "default",
        split_type: str = "random",
        release_name: Optional[str] = None,
    ):
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

        stems = build_stems(release_path, annotations_dir, annotation_type, split, partition, split_type)

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

    def get_img_info(self, index: int) -> Dict[str, Any]:
        """
        Returns the annotation information for a given image.

        Parameters
        ----------
        index : int
            The index of the image.

        Returns
        -------
        Dict[str, Any]
            A dictionary with the image's class and annotaiton information.

        Raises
        ------
        ValueError
            If there are no annotations downloaded in this machine. You can pull them by using the
            command ``darwin dataset pull $DATASET_NAME --only-annotations`` in the CLI.
        """
        if not len(self.annotations_path):
            raise ValueError("There are no annotations downloaded.")

        with self.annotations_path[index].open() as f:
            data = json.loads(f.read())["image"]
            return data

    def get_height_and_width(self, index: int) -> Tuple[float, float]:
        """
        Returns the width and height of the image with the given index.

        Parameters
        ----------
        index : int
            The index of the image.

        Returns
        -------
        Tuple[float, float]
            A tuple where the first element is the ``height`` of the image and the second is the
            ``width``.
        """
        data: Dict[str, Any] = self.get_img_info(index)
        return data["height"], data["width"]

    def extend(self, dataset: "LocalDataset", extend_classes: bool = False) -> "LocalDataset":
        """
        Extends the current dataset with another one.

        Parameters
        ----------
        dataset : Dataset
            Dataset to merge
        extend_classes : bool, default: False
            Extend the current set of classes by merging it with the set of classes belonging to the
            given dataset.

        Returns
        -------
        LocalDataset
            This ``LocalDataset`` extended with the classes of the give one.

        Raises
        ------
        ValueError

            - If the ``annotation_type`` of this ``LocalDataset`` differs from the
            ``annotation_type`` of the given one.
            - If the set of classes from this ``LocalDataset`` differs from the set of classes
            from the given one AND ``extend_classes`` is ``False``.
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

    def get_image(self, index: int) -> PILImage.Image:
        """
        Returns the correspoding ``PILImage.Image``.

        Parameters
        ----------
        index : int
            The index of the image in this ``LocalDataset``.

        Returns
        -------
        PILImage.Image
            The image.
        """
        return load_pil_image(self.images_path[index])

    def get_image_path(self, index: int) -> Path:
        """
        Returns the path of the image with the given index.

        Parameters
        ----------
        index : int
            The index of the image in this ``LocalDataset``.

        Returns
        -------
        Path
            The ``Path`` of the image.
        """
        return self.images_path[index]

    def parse_json(self, index: int) -> Dict[str, Any]:
        """
        Load an annotation and filter out the extra classes according to what is
        specified in ``self.classes`` and the ``annotation_type``.

        Parameters
        ----------
        index : int
            Index of the annotation to read.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the index and the filtered annotation.
        """
        parsed = parse_darwin_json(self.annotations_path[index], index)
        annotations = [] if parsed.is_video else parsed.annotations

        # Filter out unused classes and annotations of a different type
        if self.classes is not None:
            annotations = [
                a for a in annotations if a.annotation_class.name in self.classes and self.annotation_type_supported(a)
            ]
        return {
            "image_id": index,
            "image_path": str(self.images_path[index]),
            "height": parsed.image_height,
            "width": parsed.image_width,
            "annotations": annotations,
        }

    def annotation_type_supported(self, annotation) -> bool:
        annotation_type = annotation.annotation_class.annotation_type
        if self.annotation_type == "tag":
            return annotation_type == "tag"
        elif self.annotation_type == "bounding_box":
            is_bounding_box = annotation_type == "bounding_box"
            is_supported_polygon = (
                annotation_type in ["polygon", "complex_polygon"] and "bounding_box" in annotation.data
            )
            return is_bounding_box or is_supported_polygon
        elif self.annotation_type == "polygon":
            return annotation_type in ["polygon", "complex_polygon"]
        else:
            raise ValueError("annotation_type should be either 'tag', 'bounding_box', or 'polygon'")

    def measure_mean_std(self, multi_threaded: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes mean and std of trained images, given the train loader.

        Parameters
        ----------
        multi_threaded : bool, default: True
            Uses multiprocessing to download the dataset in parallel.

        Returns
        -------
        mean : ndarray[double]
            Mean value (for each channel) of all pixels of the images in the input folder.
        std : ndarray[double]
            Standard deviation (for each channel) of all pixels of the images in the input folder.
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

    @staticmethod
    def _compute_weights(labels: List[int]) -> np.ndarray:
        """
        Given an array of labels computes the weights normalized.

        Parameters
        ----------
        labels : List[int]
            Array of labels.

        Returns
        -------
        ndarray[float]
            Array of weights (one for each unique class) which are the inverse of their frequency.
        """
        class_support: np.ndarray = np.unique(labels, return_counts=True)[1]
        class_frequencies = class_support / len(labels)
        # Class weights are the inverse of the class frequencies
        class_weights = 1 / class_frequencies
        # Normalize vector to sum up to 1.0 (in case the Loss function does not do it)
        class_weights /= class_weights.sum()
        return class_weights

    # Loads an image with Pillow and returns the channel wise means of the image.
    @staticmethod
    def _return_mean(image_path: Path) -> np.ndarray:
        img = np.array(load_pil_image(image_path))
        mean = np.array([np.mean(img[:, :, 0]), np.mean(img[:, :, 1]), np.mean(img[:, :, 2])])
        return mean / 255.0

    # Loads an image with OpenCV and returns the channel wise std of the image.
    @staticmethod
    def _return_std(image_path: Path, mean: np.ndarray) -> Tuple[np.ndarray, float]:
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


def build_stems(
    release_path: Path,
    annotations_dir: Path,
    annotation_type: str,
    split: str,
    partition: Optional[str] = None,
    split_type: str = "random",
) -> Iterator[str]:
    """
    Builds the stems for the given release with the given annotations as base.

    Parameters
    ----------
    release_path : Path
        The path of the ``Release`` saved locally.
    annotations_dir : Path
        The path for a directory where annotations.
    annotation_type : str
        The type of the annotations.
    split : str
        The split name.
    partition : Optional[str], default: None
        How to partition files. If no partition is specified, then it takes all the json files in
        the annotations directory.
        The resulting generator prepends parent directories relative to the main annotation
        directory.

        E.g.: ``["annotations/test/1.json", "annotations/2.json", "annotations/test/2/3.json"]``:

            - annotations/test/1
            - annotations/2
            - annotations/test/2/3
    split_type str, default: "random"
        The type of split. Can be ``"random"`` or ``"stratified"``.

    Returns
    -------
    Iterator[str]
        An iterator with the path for the stem files.

    Raises
    ------
    ValueError
        If the provided ``split_type`` is invalid.

    FileNotFoundError
        If no dataset partitions are found.
    """

    if partition is None:
        return (str(e.relative_to(annotations_dir).parent / e.stem) for e in sorted(annotations_dir.glob("**/*.json")))

    if split_type == "random":
        split_filename = f"{split_type}_{partition}.txt"
    elif split_type == "stratified":
        split_filename = f"{split_type}_{annotation_type}_{partition}.txt"
    else:
        raise ValueError(f'Unknown split type "{split_type}"')

    split_path = release_path / "lists" / split / split_filename
    if split_path.is_file():
        return (e.strip("\n\r") for e in split_path.open())

    raise FileNotFoundError(
        f"could not find a dataset partition. "
        f"Split the dataset using `split_dataset()` from `darwin.dataset.split_manager`"
    )
