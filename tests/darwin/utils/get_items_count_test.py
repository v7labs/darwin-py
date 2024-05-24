# Tests for _get_item_count
from darwin.utils.get_item_count import get_item_count


def test__get_item_count_defaults_to_num_items_if_present() -> None:
    dataset_return = {
        "num_images": 2,  # Should be ignored
        "num_videos": 3,  # Should be ignored
        "num_items": 5,  # Should get this one
    }

    assert get_item_count(dataset_return) == 5


def test__get_item_count_returns_sum_of_others_if_num_items_not_present() -> None:
    dataset_return = {
        "num_images": 7,  # Should be summed
        "num_videos": 3,  # Should be summed
    }

    assert get_item_count(dataset_return) == 10


def test__get_item_count_should_tolerate_missing_members() -> None:
    assert (
        get_item_count(
            {
                "num_videos": 3,  # Should be ignored
            }
        )
        == 3
    )

    assert (
        get_item_count(
            {
                "num_images": 2,
            }
        )
        == 2
    )
