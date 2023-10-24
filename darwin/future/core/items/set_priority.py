from typing import Dict, Optional

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def set_item_priority(
    api_client: ClientCore,
    team_slug: str,
    priority: int,
    filters: Optional[Dict[str, UnknownType]] = None,
) -> JSONType:
    """
    Sets the priority of an item

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to set the priority for
    priority: int
        The priority to set

    Returns
    -------
    JSONType
    """
    payload: Dict["str", UnknownType] = {
        "priority": priority,
    }

    if filters:
        payload = {
            **payload,
            "filters": filters,
        }

    return api_client.post(
        endpoint=f"/v2/teams/{team_slug}/items/priority",
        data=payload,
    )
