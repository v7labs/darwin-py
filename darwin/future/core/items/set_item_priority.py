from typing import Dict, List
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def set_item_priority(
    api_client: ClientCore,
    team_slug: str,
    dataset_id: int,
    item_ids: List[UUID],
    priority: int,
    filters: Dict[str, UnknownType] = {},
) -> JSONType:
    """
    Sets the priority of a list of items

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to set the priority for
    dataset_id: int
        The dataset to set the priority for
    item_ids: List[UUID]
        The item ids to set the priority for
    priority: int
        The priority to set

    Returns
    -------
    JSONType
    """
    payload = {
        "priority": priority,
        "filters": {
            "item_ids": [str(item_id) for item_id in item_ids],
            "dataset_ids": [dataset_id],
            **filters,
        },
    }

    return api_client.post(
        endpoint=f"/v2/teams/{team_slug}/items/priority",
        data=payload,
    )
