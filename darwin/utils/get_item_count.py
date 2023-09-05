from typing import Dict, Optional


def get_item_count(dataset_dict: Dict) -> int:
    """
    Returns the number of items in the dataset.

    Parameters
    ----------
    dataset_dict: Dict
        The dataset dictionary.

    Returns
    -------
    int
        The number of items in the dataset.
    """
    num_items: Optional[int] = dataset_dict.get("num_items")
    num_videos: Optional[int] = dataset_dict.get("num_videos")
    num_images: Optional[int] = dataset_dict.get("num_images")

    if num_items is not None:
        return num_items

    return (num_images or 0) + (num_videos or 0)
