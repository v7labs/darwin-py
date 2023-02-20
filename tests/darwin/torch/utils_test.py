import sys
from pathlib import Path
from typing import Any, Tuple
from unittest.mock import patch

import numpy as np
import torch

from darwin.torch.utils import convert_segmentation_to_mask, flatten_masks_by_category
from tests.fixtures import *


@pytest.fixture
def masks_with_cats() -> Tuple[torch.Tensor, torch.Tensor]:
    # 3x3 'image' tensor with categories
    masks = torch.as_tensor(torch.zeros(2, 3, 3), dtype=torch.uint8)
    cats = torch.as_tensor([1, 2], dtype=torch.uint8)
    # should have 1 overlap in the corner, with the corner belonging to category '2'
    masks[0, :, 0] = 1
    masks[1, 0, :] = 1
    return masks, cats


def describe_flatten_masks() -> None:
    def it_should_raise_with_incorrect_shaped_inputs(masks_with_cats) -> None:
        masks, _ = masks_with_cats
        cats = torch.as_tensor([0], dtype=torch.uint8)
        with pytest.raises(AssertionError) as error:
            flattened = flatten_masks_by_category(masks, cats)

    def it_should_correctly_set_overlap(masks_with_cats) -> None:
        masks, cats = masks_with_cats
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats)
        assert flattened[0, 0] == 2
        unique, counts = flattened.unique(return_counts=True)
        # expected counts and uniqe now includes background class '0'
        expected_unique = torch.as_tensor([0, 1, 2], dtype=torch.uint8)
        expected_counts = torch.as_tensor([4, 2, 3], dtype=torch.uint8)
        assert torch.equal(unique, expected_unique)
        assert torch.equal(counts, expected_counts)

    def it_should_overwrite_overlap(masks_with_cats) -> None:
        masks, cats = masks_with_cats
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats, remove_overlap=True, overlap=20)
        assert flattened[0, 0] == 20
        unique, counts = flattened.unique(return_counts=True)
        expected_unique = torch.as_tensor([0, 1, 2, 20], dtype=torch.uint8)
        expected_counts = torch.as_tensor([4, 2, 2, 1], dtype=torch.uint8)
        assert torch.equal(unique, expected_unique)
        assert torch.equal(counts, expected_counts)
