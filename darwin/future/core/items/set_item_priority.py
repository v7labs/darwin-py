from __future__ import annotations

from typing import Dict, List

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def set_item_priority(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | List[int],
    priority: int,
    filters: Dict[str, UnknownType] = {},
) -> JSONType:
    """
    Sets the priority of a list of items

    Parameters
    ----------
    client: Client
        The client to use for the request.
    team_slug: str
        The slug of the team containing the items.
    dataset_id: int | List[int]
        The ID(s) of the dataset(s) containing the items.
    priority: int
        The priority to set.

    Returns
    -------
    JSONType
        The response data.
    """
    assert (
        filters
    ), "No parameters provided, please provide at least one non-dataset id filter"
    payload = {
        "filters": {
            "dataset_ids": (
                dataset_ids if isinstance(dataset_ids, list) else [dataset_ids]
            ),
            **filters,
        },
        "priority": priority,
    }

    return client.post(
        f"/v2/teams/{team_slug}/items/priority",
        data=payload,
    )
