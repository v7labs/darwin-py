import sys

import numpy as np
import pytest
from darwin.dataset.split_manager import split_dataset
from tests.fixtures import *


def test_requires_scikit_learn():
    sys.modules["sklearn"] = None

    with pytest.raises(ImportError):
        split_dataset("")


def describe_classification_dataset():
    @pytest.mark.parametrize("val_percentage,test_percentage", [(0, 0.3), (0, 0), (0.2, 0), (0.5, 0.5), (1, 0.1)])
    def it_raises_for_invalid_split_configuration(
        team_slug: str, team_extracted_dataset_path: Path, val_percentage: float, test_percentage: float
    ):
        with pytest.raises(ValueError):
            root = team_extracted_dataset_path / team_slug / "sl"
            split_dataset(root, release_name="latest", val_percentage=val_percentage, test_percentage=test_percentage)

    @pytest.mark.parametrize("val_percentage,test_percentage", [(0.2, 0.3), (0.3, 0.2)])
    def it_should_split_a_dataset(
        team_slug: str, team_extracted_dataset_path: Path, val_percentage: float, test_percentage: float
    ):
        root = team_extracted_dataset_path / team_slug / "sl"

        train_percentage: float = 1 - val_percentage - test_percentage

        tot_size: int = len(list((root / "images").glob("*")))
        splits: Path = split_dataset(
            root, release_name="latest", val_percentage=val_percentage, test_percentage=test_percentage
        )

        sizes = (train_percentage, val_percentage, test_percentage)
        names = ("train", "val", "test")

        for size, name in zip(sizes, names):
            with open(splits / f"random_{name}.txt", "r") as f:
                lines_len = len([l for l in f.readlines() if l.strip() != ""])
                local_size = lines_len / tot_size, size
                assert np.allclose(local_size, size, atol=1e-3)
