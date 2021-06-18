import sys

from darwin.dataset.split_manager import split_dataset


def test_requires_scikit_learn():
    sys.modules["sklearn"] = None

    # split_dataset returns a pathlib.Path object when successful.
    # However, it returns None when it catches an ImportError for scikit-learn.
    assert split_dataset("") is None
