import unittest

import pytest

from darwin.future.data_objects.darwin import Dataset, Release, Team


def test_Dataset() -> None:
    dataset = Dataset("test")
    assert dataset.name == "test"
    dataset = Dataset(2)


if __name__ == "__main__":
    pytest.main()
