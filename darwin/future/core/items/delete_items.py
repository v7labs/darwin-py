from __future__ import annotations

from typing import Dict, List, Literal
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def delete_list_of_items(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int] | Literal["all"],
    item_ids: List[UUID],
    filters: Dict[str, UnknownType] = {},
) -> JSONType:
    """
    Delete specified items

    Parameters
    ----------
    client: Client
        The client to use for the request.
    team_slug: str
        The slug of the team containing the items.
    dataset_ids: int | List[int]
        The ID(s) of the dataset(s) containing the items.
    filters: Dict[str, UnknownType]
        Filter parameters

    Returns
    -------
    JSONType
        The response data.
    """
    payload = {
        "filters": {
            "dataset_ids": [str(item) for item in dataset_ids]
            if isinstance(dataset_ids, list)
            else [str(dataset_ids)],
            "item_ids": [str(item_id) for item_id in item_ids],
            **filters,
        }
    }
    return client.delete(f"/v2/teams/{team_slug}/items", data=payload)
