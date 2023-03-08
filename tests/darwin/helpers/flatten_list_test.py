import pytest

from darwin.helpers import flatten_list


def test_raises_if_passed_non_array() -> None:
    with pytest.raises(TypeError):
        flatten_list("string")  # type: ignore


def test_returns_empty_list_if_passed_empty_list() -> None:
    assert flatten_list([]) == []


def test_returns_list_if_passed_list() -> None:
    assert flatten_list([1, 2, 3]) == [1, 2, 3]


def test_returns_flattened_list_if_passed_nested_list() -> None:
    assert flatten_list([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_returns_flattened_list_if_passed_nested_list_with_different_depth() -> None:
    assert flatten_list([[1, 2], [3, [4, 5]]]) == [1, 2, 3, 4, 5]


# Makes file directly runnable with python
if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main(["-v", "-x", __file__]))
