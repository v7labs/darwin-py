import sys

import pytest
from darwin.dataset.split_manager import split_dataset


def test_requires_scikit_learn():
    sys.modules["sklearn"] = None

    with pytest.raises(ImportError):
        split_dataset("")
