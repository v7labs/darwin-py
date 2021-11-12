from pathlib import Path

import numpy as np
from darwin.torch.dataset import ClassificationDataset, InstanceSegmentationDataset
from tests.fixtures import *


def generic_dataset_test(ds, n, size):
    weights = ds.measure_weights()
    img = ds[0][0]
    assert img.size[0] == size[0] and img.size[1] == size[1]
    assert len(weights) == len(ds.classes)
    assert np.isclose(np.sum(weights), 1)
    assert len(ds) == n


def describe_classification_dataset():
    def it_should_correctly_create_a_single_label_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "sl"

        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=5, size=(50, 50))
        assert not ds.is_multi_label

    def it_should_correctly_create_a_multi_label_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "ml"

        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=5, size=(50, 50))
        assert ds.is_multi_label

    def it_should_correctly_create_a_instance_seg_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "coco"

        ds = InstanceSegmentationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=5, size=(50, 50))
        assert type(ds[0][1]) is dict
