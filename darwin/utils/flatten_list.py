from typing import Generator, List

from darwin.datatypes import UnknownType


def flatten_list(list_of_lists: List[UnknownType]) -> List[UnknownType]:
    """
    Flattens a list of lists into a single list.

    Parameters
    ----------
    list_of_lists : List[List[Any]]
        The list of lists to flatten.

    Returns
    -------
    List[Any]
        The flattened list.
    """

    if not isinstance(list_of_lists, list):
        raise TypeError("Expected a list")

    def flatten(lists: List[UnknownType]) -> Generator[list, UnknownType, UnknownType]:
        if isinstance(lists, list) and len(lists) == 0:
            return lists
        for item in lists:
            if isinstance(item, list):
                for i in flatten(item):
                    yield i
            else:
                yield item

    return list(flatten(list_of_lists))
