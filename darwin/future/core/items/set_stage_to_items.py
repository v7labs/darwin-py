from __future__ import annotations

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.typing import UnknownType


def set_stage_to_items(
    client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int],
    stage_id: str,
    workflow_id: str,
    filters: dict[str, UnknownType],
) -> JSONType:
    """
    Sets stage to multiple items matched by filters.

    Args:
        client (ClientCore): The Darwin Core client.
        team_slug (str): The team slug.
        stage_id (str): The stage id.
        workflow_id (str): The workflow id.
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
        "stage_id": stage_id,
        "workflow_id": workflow_id,
    }

    return client.post(f"/v2/teams/{team_slug}/items/stage", data=payload)
