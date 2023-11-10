from __future__ import annotations

from typing import Dict, List, Literal
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def delete_list_of_items(
    api_client: ClientCore,
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
        The client to use for the request
    team_slug: str
        The slug of the team containing the items
    dataset_id: int
        The ID of the dataset containing the items
    item_ids: List[UUID]
        The IDs of the items to be deleted
    filters: Dict[str, UnknownType]
        Dataset filter parameters

    Returns
    -------
    JSONType
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

    return api_client.delete(f"/v2/teams/{team_slug}/items", data=payload)
