from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses

from darwin.client import Client
from darwin.config import Config
from darwin.dataset import download_manager as dm
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.remote_dataset_v1 import RemoteDatasetV1
from tests.fixtures import *


def test_parse_manifests() -> None:
    paths = [
        Path("tests/darwin/dataset/data/manifest_examples/manifest_1.txt"),
        Path("tests/darwin/dataset/data/manifest_examples/manifest_2.txt"),
    ]
    segment_manifests = dm._parse_manifests(paths, "0")
    assert len(segment_manifests) == 4
    assert len(segment_manifests[0].items) == 2
    assert len(segment_manifests[1].items) == 2
    assert len(segment_manifests[2].items) == 2
    assert len(segment_manifests[3].items) == 2
    assert segment_manifests[0].items[0].absolute_frame == 0
    assert segment_manifests[0].items[1].absolute_frame == 1
    assert segment_manifests[0].items[1].visibility == True
    assert segment_manifests[1].items[0].absolute_frame == 2
    assert segment_manifests[1].items[1].absolute_frame == 3
    assert segment_manifests[1].items[1].visibility == True
    assert segment_manifests[2].items[0].absolute_frame == 4
    assert segment_manifests[2].items[1].absolute_frame == 5
    assert segment_manifests[2].items[1].visibility == True
    assert segment_manifests[3].items[0].absolute_frame == 6
    assert segment_manifests[3].items[1].absolute_frame == 7
    assert segment_manifests[3].items[1].visibility == True
