from typing import List, Tuple

import numpy as np
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
    # should have 1 overlap in the corner, with the corner belonging to category '2'
    masks[0, :, :] = 1
    masks[1, 0, :] = 1
    masks[2, :, 0] = 1
    return masks, cats


def describe_flatten_masks() -> None:
    def it_should_raise_with_incorrect_shaped_inputs(basic_masks_with_cats) -> None:
        masks, _ = basic_masks_with_cats
        cats = [0]
        with pytest.raises(AssertionError) as error:
            flattened = flatten_masks_by_category(masks, cats)

    def it_should_correctly_set_overlap(basic_masks_with_cats) -> None:
        masks, cats = basic_masks_with_cats
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats)
        assert flattened[0, 0] == 2
        unique, counts = flattened.unique(return_counts=True)
        # expected counts and uniqe now includes background class '0'
        expected_unique = torch.as_tensor([0, 1, 2], dtype=torch.uint8)
        expected_counts = torch.as_tensor([4, 2, 3], dtype=torch.uint8)
        assert torch.equal(unique, expected_unique)
        assert torch.equal(counts, expected_counts)

    def it_should_handle_fully_masked_image(multiple_overlap_masks) -> None:
        masks, cats = multiple_overlap_masks
        flattened: torch.Tensor = flatten_masks_by_category(masks, cats)
        assert 0 not in np.unique(flattened)

    def it_should_handle_multiple_overlaps(multiple_overlap_masks) -> None:
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
