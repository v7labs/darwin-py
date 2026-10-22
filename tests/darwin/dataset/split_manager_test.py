import logging
import sys
from pathlib import Path

import numpy as np
import pytest

from darwin.dataset.split_manager import _stratify_samples, split_dataset
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
                lines_len = len([line for line in f.readlines() if line.strip() != ""])
                local_size = lines_len / tot_size, size
                assert np.allclose(local_size, size, atol=1e-3)


# Production Gust object-detection split: 218 items, 15% val, 15% test.
_GUST_SIZE = 218
_GUST_TRAIN = 152
_GUST_VAL = 33
_GUST_TEST = 33
_SEEDS = range(20)


def _labels(n, rare_count=0, cooccur=False, rare_name="rare", common_name="tassel"):
    labels = {i: {common_name} for i in range(n)}
    for index in range(rare_count):
        if cooccur:
            labels[index] = {common_name, rare_name}
        else:
            labels[index] = {rare_name}
    return labels


def _partition_like_stratified_split(
    idx_to_classes, seed, train_size, val_size, test_size
):
    """Run `_stratify_samples` and the padding loop from `_stratified_split`."""
    train, val, test = _stratify_samples(
        idx_to_classes, seed, train_size, val_size, test_size
    )
    repeated = _stratify_samples(idx_to_classes, seed, train_size, val_size, test_size)
    assert (train, val, test) == repeated

    train, val, test = list(train), list(val), list(test)
    stratified_indices = train + val + test
    for idx in range(train_size + val_size + test_size):
        if idx in stratified_indices:
            continue
        if len(train) < train_size:
            train.append(idx)
        elif len(val) < val_size:
            val.append(idx)
        else:
            test.append(idx)
    return train, val, test


def _assert_partition(train, val, test, train_size, val_size, test_size, context):
    assert (len(train), len(val), len(test)) == (
        train_size,
        val_size,
        test_size,
    ), context
    train_ids, val_ids, test_ids = set(train), set(val), set(test)
    assert len(train_ids) == len(train), context
    assert len(val_ids) == len(val), context
    assert len(test_ids) == len(test), context
    assert train_ids.isdisjoint(val_ids), context
    assert train_ids.isdisjoint(test_ids), context
    assert val_ids.isdisjoint(test_ids), context
    assert train_ids | val_ids | test_ids == set(
        range(train_size + val_size + test_size)
    ), context


class TestStratifiedSplitLowSupport:
    """Rare classes are valid data. The stratified split must not raise."""

    @pytest.mark.parametrize("seed", _SEEDS)
    def test_single_class_dataset(self, seed, caplog):
        labels = _labels(_GUST_SIZE)
        with caplog.at_level(logging.WARNING):
            train, val, test = _partition_like_stratified_split(
                labels, seed, _GUST_TRAIN, _GUST_VAL, _GUST_TEST
            )
        assert not caplog.records
        _assert_partition(
            train, val, test, _GUST_TRAIN, _GUST_VAL, _GUST_TEST, f"seed {seed}"
        )

    @pytest.mark.parametrize("rare_count", [1, 2, 3, 4, 5])
    def test_exclusive_rare_class(self, rare_count):
        labels = _labels(_GUST_SIZE, rare_count=rare_count, cooccur=False)
        for seed in _SEEDS:
            context = f"exclusive rare={rare_count} seed={seed}"
            train, val, test = _partition_like_stratified_split(
                labels, seed, _GUST_TRAIN, _GUST_VAL, _GUST_TEST
            )
            _assert_partition(
                train, val, test, _GUST_TRAIN, _GUST_VAL, _GUST_TEST, context
            )
            rare = set(range(rare_count))
            if rare_count == 1:
                assert rare <= set(train), context
            elif rare_count < 5:
                # One instance is held out of the val/test stratified split and
                # lands in val. The rest stay in train. Stratification of the
                # remaining labels is preserved.
                assert rare.isdisjoint(test), context
                assert len(rare & set(val)) == 1, context
                assert len(rare & set(train)) == rare_count - 1, context

    @pytest.mark.parametrize("rare_count", list(range(1, 12)))
    def test_cooccurring_rare_class(self, rare_count):
        labels = _labels(_GUST_SIZE, rare_count=rare_count, cooccur=True)
        for seed in _SEEDS:
            context = f"co-occurring rare={rare_count} seed={seed}"
            train, val, test = _partition_like_stratified_split(
                labels, seed, _GUST_TRAIN, _GUST_VAL, _GUST_TEST
            )
            _assert_partition(
                train, val, test, _GUST_TRAIN, _GUST_VAL, _GUST_TEST, context
            )

    def test_first_split_when_classes_exceed_test_slots(self):
        # 80 classes of 2 images: val+test has 66 slots, so the first
        # stratified split cannot place every class.
        labels = {}
        index = 0
        for class_id in range(80):
            labels[index] = {f"c{class_id}"}
            index += 1
            labels[index] = {f"c{class_id}"}
            index += 1
        while index < _GUST_SIZE:
            labels[index] = {"filler"}
            index += 1
        for seed in _SEEDS:
            train, val, test = _partition_like_stratified_split(
                labels, seed, _GUST_TRAIN, _GUST_VAL, _GUST_TEST
            )
            _assert_partition(
                train,
                val,
                test,
                _GUST_TRAIN,
                _GUST_VAL,
                _GUST_TEST,
                f"many classes seed={seed}",
            )

    def test_second_split_when_val_is_smaller_than_class_count(self):
        # val 10 / test 40. After the first split, y_tmp still has more
        # classes than the validation side of the second split.
        dataset_size = 100
        val_size = 10
        test_size = 40
        train_size = dataset_size - val_size - test_size
        labels = {i: {f"r{i // 4}"} for i in range(48)}
        for index in range(48, dataset_size):
            labels[index] = {"main"}
        for seed in _SEEDS:
            train, val, test = _partition_like_stratified_split(
                labels, seed, train_size, val_size, test_size
            )
            _assert_partition(
                train,
                val,
                test,
                train_size,
                val_size,
                test_size,
                f"small val seed={seed}",
            )

    @pytest.mark.parametrize("seed", _SEEDS)
    def test_several_singleton_classes(self, seed):
        labels = _labels(_GUST_SIZE, rare_count=0)
        for index in range(10):
            labels[index] = {f"singleton-{index}"}
        train, val, test = _partition_like_stratified_split(
            labels, seed, _GUST_TRAIN, _GUST_VAL, _GUST_TEST
        )
        _assert_partition(
            train, val, test, _GUST_TRAIN, _GUST_VAL, _GUST_TEST, f"seed {seed}"
        )
