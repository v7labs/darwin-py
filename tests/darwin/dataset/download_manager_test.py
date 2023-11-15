from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest
import responses
from requests import get

from darwin.client import Client
from darwin.config import Config
from darwin.dataset import download_manager as dm
from darwin.dataset.identifier import DatasetIdentifier
from darwin.dataset.remote_dataset_v1 import RemoteDatasetV1
from darwin.datatypes import Slot
from tests.fixtures import *


@pytest.fixture
def manifest_paths() -> List[Path]:
    return [
        Path("tests/darwin/dataset/data/manifest_examples/manifest_1.txt.test"),
        Path("tests/darwin/dataset/data/manifest_examples/manifest_2.txt.test"),
    ]


@pytest.fixture
def slot_w_manifests() -> Slot:
    return Slot(
        name="test_slot",
        type="video",
        source_files=[],
        frame_manifest=[{"url": "http://test.com"}, {"url": "http://test2.com"}],
    )


def test_parse_manifests(manifest_paths: List[Path]) -> None:
    segment_manifests = dm._parse_manifests(manifest_paths, "0")
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


def test_get_segment_manifests(
    manifest_paths: List[Path], slot_w_manifests: Slot
) -> None:
    parent_path = Path("tests/darwin/dataset/data/manifest_examples")
    files = [open(path, "r").read() for path in manifest_paths]
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://test.com", body=files[0])
        rsps.add(responses.GET, "http://test2.com", body=files[1])
        segment_manifests = dm.get_segment_manifests(slot_w_manifests, parent_path, "")
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
