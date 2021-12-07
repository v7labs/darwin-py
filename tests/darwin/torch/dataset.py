from pathlib import Path

import numpy as np
from darwin.torch.dataset import (
    ClassificationDataset,
    InstanceSegmentationDataset,
    ObjectDetectionDataset,
    SemanticSegmentationDataset,
)
from tests.fixtures import *

import torch


def generic_dataset_test(ds, n, size):
    weights = ds.measure_weights()
    img = ds[0][0]
    assert img.shape[-2] == size[0] and img.shape[-1] == size[1]
    assert len(weights) == len(ds.classes)
    assert np.isclose(np.sum(weights), 1)
    assert len(ds) == n


def describe_classification_dataset():
    def it_should_correctly_create_a_single_label_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "sl"

        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert not ds.is_multi_label

    def it_should_correctly_create_a_multi_label_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "ml"

        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert ds.is_multi_label


def describe_instance_seg_dataset():
    def it_should_correctly_create_a_instance_seg_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "coco"

        ds = InstanceSegmentationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert type(ds[0][1]) is dict


def describe_semantic_seg_dataset():
    def it_should_correctly_create_a_semantic_seg_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "coco"

        ds = SemanticSegmentationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert type(ds[0][1]) is dict


def describe_object_detection_dataset():
    def it_should_correctly_create_a_object_detection_dataset(test_datasets_dir: Path):

        root = test_datasets_dir / "data" / "coco"

        ds = ObjectDetectionDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert type(ds[0][1]) is dict
        img, target = ds[0]

        for bbox in target["boxes"]:
            assert bbox.shape[-1] == 4
            assert torch.all(bbox > 0)
            # check if xs are > than the width
            assert torch.all(bbox[::2] < img.shape[-1])
            # check if yts are > than the height
            assert torch.all(bbox[1::2] < img.shape[-2])
