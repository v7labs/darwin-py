

from typing import List
from uuid import UUID

from darwin.future.core.client import Client


def move_items_to_stage(api_client: Client, team_slug: str, dataset_id: int, stage_id: UUID, item_ids: List[UUID]) -> None:
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

    api_client.post(
        f"/v2/teams/{team_slug}/items/stage", {"item_ids": [str(item_id) for item_id in item_ids]}
    )