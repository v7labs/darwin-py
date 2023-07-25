from typing import List
from uuid import UUID

from darwin.future.core.client import Client, JSONType


def move_items_to_stage(
    api_client: Client, team_slug: str, workflow_id: UUID, dataset_id: int, stage_id: UUID, item_ids: List[UUID]
) -> JSONType:
    """
    Moves a list of items to a stage

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to move items for
    dataset_id: str
        The id or slug of the dataset to move items for
    stage_id: str
        The id or slug of the stage to move items to
    item_ids: List[UUID]
        A list of item ids to move to the stage

    Returns
    -------
    None
    """

    return api_client.post(
        f"/v2/teams/{team_slug}/items/stage",
        {
            "filters": {
                "dataset_ids": [dataset_id],
                "item_ids": [str(id) for id in item_ids],
            },
            "stage_id": str(stage_id),
            "workflow_id": str(workflow_id),
        },
    )
