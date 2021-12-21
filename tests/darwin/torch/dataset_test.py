import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
from darwin.torch.dataset import (
    ClassificationDataset,
    InstanceSegmentationDataset,
    ObjectDetectionDataset,
    SemanticSegmentationDataset,
    get_dataset,
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
    def it_should_correctly_create_a_single_label_dataset(team_slug: str, team_extracted_dataset_path: Path):
        root = team_extracted_dataset_path / team_slug / "sl"
        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert not ds.is_multi_label

    def it_should_correctly_create_a_multi_label_dataset(team_slug: str, team_extracted_dataset_path: Path):
        root = team_extracted_dataset_path / team_slug / "ml"
        ds = ClassificationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert ds.is_multi_label


def describe_instance_seg_dataset():
    def it_should_correctly_create_a_instance_seg_dataset(team_slug: str, team_extracted_dataset_path: Path):
        root = team_extracted_dataset_path / team_slug / "coco"
        ds = InstanceSegmentationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert type(ds[0][1]) is dict


def describe_semantic_seg_dataset():
    def it_should_correctly_create_a_semantic_seg_dataset(team_slug: str, team_extracted_dataset_path: Path):
        root = team_extracted_dataset_path / team_slug / "coco"
        ds = SemanticSegmentationDataset(dataset_path=root, release_name="latest")

        generic_dataset_test(ds, n=20, size=(50, 50))
        assert type(ds[0][1]) is dict


def describe_object_detection_dataset():
    def it_should_correctly_create_a_object_detection_dataset(team_slug: str, team_extracted_dataset_path: Path):
        root = team_extracted_dataset_path / team_slug / "coco"
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


def describe_get_dataset():
    def it_exits_when_dataset_not_supported():
        with patch.object(sys, "exit") as exception:
            get_dataset("test", "unknown")
            exception.assert_called_once_with(1)

    def it_exits_when_dataset_does_not_exist_locally():
        with patch.object(sys, "exit") as exception:
            get_dataset("test", "classification")
            exception.assert_called_once_with(1)

    def it_loads_classification_dataset(local_config_file: Config, team_extracted_dataset_path: Path):
        dataset = get_dataset("sl", "classification")
        assert isinstance(dataset, ClassificationDataset)
        assert len(dataset) == 20

        image, label = dataset[0]
        assert image.size() == (3, 50, 50)
        assert label.item() == 0

    def it_loads_object_detection_dataset(local_config_file: Config, team_extracted_dataset_path: Path):
        dataset = get_dataset("coco", "object-detection")
        assert isinstance(dataset, ObjectDetectionDataset)
        assert len(dataset) == 20

        image, label = dataset[0]
        assert image.size() == (3, 50, 50)

        label = {k: v.numpy().tolist() for k, v in label.items()}
        assert label == {
            "boxes": [[37, 8, 30, 13], [43, 14, 10, 7]],
            "area": [390, 70],
            "labels": [0, 0],
            "image_id": [0],
            "iscrowd": [0, 0],
        }

    def it_loads_instance_segmentation_dataset(local_config_file: Config, team_extracted_dataset_path: Path):
        dataset = get_dataset("coco", "instance-segmentation")
        assert isinstance(dataset, InstanceSegmentationDataset)
        assert len(dataset) == 20

        image, label = dataset[0]
        assert image.size() == (3, 50, 50)

        label = {k: _maybe_tensor_to_list(v) for k, v in label.items()}

        assert label["boxes"] == [[8.0, 14.0, 50.0, 50.0], [37.0, 24.0, 50.0, 50.0]]
        assert label["area"] == [0.0, 0.0]
        assert label["labels"] == [0, 0]
        assert label["image_id"] == [0]
        assert label["iscrowd"] == [0, 0]
        assert label["height"] == 50
        assert label["image_path"] == f"{dataset.dataset_path}/images/16.png"
        assert label["width"] == 50


def _maybe_tensor_to_list(arg: Any) -> Any:
    if isinstance(arg, torch.Tensor):
        return arg.numpy().tolist()
    return arg
