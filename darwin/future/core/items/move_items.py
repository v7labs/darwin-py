from __future__ import annotations

from typing import Dict, List
from uuid import UUID

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def move_items_to_stage(
    client: ClientCore,
    team_slug: str,
    workflow_id: UUID,
    dataset_ids: int | List[int],
    stage_id: UUID,
    filters: Dict[str, UnknownType] = {},
) -> JSONType:
    """
    Moves a list of items to a stage

    Parameters
    ----------
    client: Client
        The client to use for the request.
    team_slug: str
        The slug of the team to move items for.
    workflow_id: UUID
        The id of the workflow to move items for.
    dataset_ids: int | List[int]
        The ID(s) of the dataset(s) containing the items.
    stage_id: UUID
        The id of the workflow to move items for.
    filters: Dict[str, UnknownType]
        Filter parameters.

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
        "stage_id": str(stage_id),
        "workflow_id": str(workflow_id),
    }

    return client.post(f"/v2/teams/{team_slug}/items/stage", data=payload)
