from __future__ import annotations

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONDict, JSONType


def assign_items(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int],
    assignee_id: int,
    workflow_id: str,
    filters: JSONDict,
) -> JSONType:
    """
    Assign a user to all items matched by filters.

    Args:
        client (ClientCore): The Darwin Core client.
        team_slug (str): The team slug.
        dataset_ids (int | list[int]): The dataset ids.
        assignee_id (int): The user id to assign.
        workflow_id (str): The workflow id that selected items have to belong to.
        filters Dict[str, UnknownType]: The parameters of the filter.

    Returns:
        JSONType: The response data.
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
        "assignee_id": assignee_id,
        "workflow_id": workflow_id,
    }

    return client.post(f"/v2/teams/{team_slug}/items/assign", data=payload)
