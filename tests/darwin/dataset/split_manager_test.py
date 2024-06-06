import sys

import numpy as np
import pytest

from darwin.dataset.split_manager import split_dataset
from darwin.utils import SUPPORTED_IMAGE_EXTENSIONS
from tests.fixtures import *


def test_requires_scikit_learn():
    sklearn_module = sys.modules.get("sklearn")
    sys.modules["sklearn"] = None

    try:
        with pytest.raises(ImportError):
            split_dataset("")
    finally:
        del sys.modules["sklearn"]
        if sklearn_module:
            sys.modules["sklearn"] = sklearn_module


class TestClassificationDataset:
    @pytest.mark.parametrize(
        "val_percentage,test_percentage",
        [(0, 0.3), (0, 0), (0.2, 0), (0.5, 0.5), (1, 0.1)],
    )
    def test_raises_for_invalid_split_configuration(
        self,
        team_slug_darwin_json_v2: str,
        team_extracted_dataset_path: Path,
        val_percentage: float,
        test_percentage: float,
    ):
        with pytest.raises(ValueError):
            root = team_extracted_dataset_path / team_slug_darwin_json_v2 / "sl"
            split_dataset(
                root,
                release_name="latest",
                val_percentage=val_percentage,
                test_percentage=test_percentage,
            )

    @pytest.mark.parametrize("val_percentage,test_percentage", [(0.2, 0.3), (0.3, 0.2)])
    def test_should_split_a_dataset(
        self,
        team_slug_darwin_json_v2: str,
        team_extracted_dataset_path: Path,
        val_percentage: float,
        test_percentage: float,
    ):
        root = team_extracted_dataset_path / team_slug_darwin_json_v2 / "sl"

        train_percentage: float = 1 - val_percentage - test_percentage

        tot_size = sum(
            1
            for file in (root / "images").glob("*")
            if file.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        )
        splits: Path = split_dataset(
            root,
            release_name="latest",
            val_percentage=val_percentage,
            test_percentage=test_percentage,
        )

        sizes = (train_percentage, val_percentage, test_percentage)
        names = ("train", "val", "test")

        for size, name in zip(sizes, names):
            with open(splits / f"random_{name}.txt", "r") as f:
                lines_len = len([l for l in f.readlines() if l.strip() != ""])
                local_size = lines_len / tot_size, size
                assert np.allclose(local_size, size, atol=1e-3)
