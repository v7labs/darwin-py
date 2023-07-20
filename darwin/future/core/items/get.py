from typing import List, Union
from uuid import UUID

from darwin.future.core.client import Client
from darwin.future.core.types.common import QueryString


def get_item_ids(api_client: Client, team_slug: str, dataset_id: Union[str, int]) -> List[UUID]:
    """
    Returns a list of item ids for the dataset

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to get item ids for
    dataset_id: str
        The id or slug of the dataset to get item ids for

    Returns
    -------
    List[UUID]
        A list of item ids
    """

    response = api_client.get(
        f"/v2/teams/{team_slug}/items/ids",
        QueryString({"not_statuses": "archived,error", "sort[id]": "desc", "dataset_ids": str(dataset_id)}),
    )
    assert type(response) == dict
    uuids = [UUID(uuid) for uuid in response["item_ids"]]
    return uuids


def get_item_ids_stage(
    api_client: Client, team_slug: str, dataset_id: Union[int, str], stage_id: Union[UUID, str]
) -> List[UUID]:
    """
    Returns a list of item ids for the stage

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to get item ids for
    dataset_id: str
        The id or slug of the dataset to get item ids for
    stage_id: str
        The id or slug of the stage to get item ids for

    Returns
    -------
    List[UUID]
        A list of item ids
    """
    response = api_client.get(
        f"/v2/teams/{team_slug}/items/ids",
        QueryString({"workflow_stage_ids": str(stage_id), "dataset_ids": str(dataset_id)}),
    )
    assert type(response) == dict
    uuids = [UUID(uuid) for uuid in response["item_ids"]]
    return uuids
