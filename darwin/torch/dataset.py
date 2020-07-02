from typing import List, Optional

import numpy as np

from darwin.cli_functions import _error, _load_client
from darwin.dataset import LocalDataset
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.utils import load_pil_image
from darwin.torch.transforms import Compose, ConvertPolygonsToInstanceMasks, ConvertPolygonsToSemanticMask
from darwin.torch.utils import polygon_area
from darwin.utils import convert_polygons_to_sequences


def get_dataset(
    dataset_slug: str,
    dataset_type: str,
    partition: Optional[str] = None,
    split: str = "default",
    split_type: str = "random",
    transform: Optional[List] = None,
):
    """ Creates and returns a dataset

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

    for p in client.list_deprecated_local_datasets(team=identifier.team_slug):
        if identifier.dataset_slug == p.name:
            _error(
                f"Found a local version of the dataset {identifier.dataset_slug} which uses a deprecated format. "
                f"Run `darwin dataset migrate {identifier}` if you want to be able to use it in darwin-py."
            )

    _error(
        f"Dataset '{identifier.dataset_slug}' does not exist locally. "
        f"Use 'darwin dataset remote' to see all the available datasets, "
        f"and 'darwin dataset pull' to pull them."
    )


class ClassificationDataset(LocalDataset):
    def __init__(self, transform: Optional[List] = None, **kwargs):
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
            image_path: str
                The path to the image on the file system
            category_id : int
                The single label of the image selected
        """
        img = load_pil_image(self.images_path[index])
        if self.transform is not None:
            img = self.transform(img)

        target = self.parse_json(index)
        annotations = target.pop("annotations")
        tags = [self.classes.index(a["name"]) for a in annotations if "tag" in a]
        if len(tags) > 1:
            raise ValueError(f"Multiple tags defined for this image ({tags}). This is not supported at the moment.")
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


class InstanceSegmentationDataset(LocalDataset):
    def __init__(self, transform: Optional[List] = None, **kwargs):
        """See `LocalDataset` class for documentation"""
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
        img = load_pil_image(self.images_path[index])
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


class SemanticSegmentationDataset(LocalDataset):
    def __init__(self, transform: Optional[List] = None, **kwargs):
        """See `LocalDataset` class for documentation"""
        super().__init__(annotation_type="polygon", **kwargs)

        self.transform = transform
        if self.transform is not None and isinstance(self.transform, list):
            self.transform = Compose(self.transform)

        self.convert_polygons = ConvertPolygonsToSemanticMask()

    def __getitem__(self, index: int):
        """See superclass for documentation

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
        img = load_pil_image(self.images_path[index])
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
