from pathlib import Path

import numpy as np
from darwin.torch.dataset import ClassificationDataset
from pets.builders import (
    DarwinMultiLabelDatasetBuilder,
    DarwinSingleLabelDatasetBuilder,
)
from pets.datasets import GridRandomColoursDataset, RandomColoursDataset


def describe_classification_dataset():
    def it_should_correctly_create_a_single_label_dataset(tmp_path: Path):
        ds = RandomColoursDataset(size=(100, 100))
        # the name of the dataset that will created on darwin
        name = "test-single"
        # root is used to locally store the dataset
        root = tmp_path / name
        builder = DarwinSingleLabelDatasetBuilder(root, name, ds)
        builder()
        # add the classes .txt file
        list_dir = root / "releases" / "latest" / "lists"
        list_dir.mkdir(exist_ok=True, parents=True)

        classes_file = list_dir / "classes_tag.txt"
        classes_names = ds.idx2names.values()
        with classes_file.open("w") as f:
            f.write("\n".join(classes_names))

        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        weights = ds.measure_weights()

        assert len(weights) == len(classes_names)
        assert np.isclose(np.sum(weights), 1)
        assert not ds.is_multi_label

    def it_should_correctly_create_a_multi_label_dataset(tmp_path: Path):
        ds = GridRandomColoursDataset(size=(100, 100))
        # the name of the dataset that will created on darwin
        name = "test-multi"
        # root is used to locally store the dataset
        root = tmp_path / name
        builder = DarwinMultiLabelDatasetBuilder(root, name, ds)
        builder()
        # add the classes .txt file
        list_dir = root / "releases" / "latest" / "lists"
        list_dir.mkdir(exist_ok=True, parents=True)

        classes_file = list_dir / "classes_tag.txt"
        classes_names = ds.idx2names.values()
        with classes_file.open("w") as f:
            f.write("\n".join(classes_names))

        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        weights = ds.measure_weights()

        assert len(weights) == len(classes_names)
        assert np.isclose(np.sum(weights), 1)
        assert ds.is_multi_label
