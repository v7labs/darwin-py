from typing import List, Tuple

import numpy as np
import pytest
import torch

from darwin.torch.utils import flatten_masks_by_category
from tests.fixtures import *


@pytest.fixture
def basic_masks_with_cats() -> Tuple[torch.Tensor, List[int]]:
    # 3x3 'image' tensor with categories
    masks = torch.as_tensor(torch.zeros(2, 3, 3), dtype=torch.uint8)
    cats = [1, 2]
    # should have 1 overlap in the corner, with the corner belonging to category '2'
    masks[0, :, 0] = 1
    masks[1, 0, :] = 1
    return masks, cats


@pytest.fixture
def multiple_overlap_masks() -> Tuple[torch.Tensor, List[int]]:
    """
    Describes a test where annotations are staggered on top of each other but share a class
    for example, a billboard that sits in front of one building, but partially behind another
    """
    masks = torch.as_tensor(torch.zeros(3, 3, 3), dtype=torch.uint8)
    cats = [1, 2, 1]
    # should have 1 overlap in the corner, with the corner belonging to category '1'
    masks[0, :, :] = 1
    masks[1, 0, :] = 1
    masks[2, :, 0] = 1
    return masks, cats


class TestFlattenMasks:
    def test_should_raise_with_incorrect_shaped_inputs(self, basic_masks_with_cats: Tuple) -> None:
        masks, _ = basic_masks_with_cats
        cats = [0]
        with pytest.raises(AssertionError) as error:
            flattened = flatten_masks_by_category(masks, cats)

    def test_should_correctly_set_overlap(self, basic_masks_with_cats: Tuple) -> None:
        masks, cats = basic_masks_with_cats
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats)
        assert flattened[0, 0] == 2
        unique, counts = flattened.unique(return_counts=True)
        # expected counts and uniqe now includes background class '0'
        expected_unique = torch.as_tensor([0, 1, 2], dtype=torch.uint8)
        expected_counts = torch.as_tensor([4, 2, 3], dtype=torch.uint8)
        assert torch.equal(unique, expected_unique)
        assert torch.equal(counts, expected_counts)

    def test_should_handle_fully_masked_image(self, multiple_overlap_masks: Tuple) -> None:
        masks, cats = multiple_overlap_masks
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats)
        assert 0 not in np.unique(flattened)

    def test_should_handle_multiple_overlaps(self, multiple_overlap_masks: Tuple) -> None:
        masks, cats = multiple_overlap_masks
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats)
        unique, counts = flattened.unique(return_counts=True)
        assert flattened[0, 0] == 1
        assert flattened[0, 1] == 2
        assert flattened[0, 2] == 2
        expected_unique = torch.as_tensor([1, 2], dtype=torch.uint8)
        expected_counts = torch.as_tensor([7, 2], dtype=torch.uint8)
        assert torch.equal(unique, expected_unique)
        assert torch.equal(counts, expected_counts)
