from typing import List, Optional, Union
from uuid import UUID

from pydantic import parse_obj_as

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.item import Item


def get_item_ids(
    api_client: ClientCore, team_slug: str, dataset_id: Union[str, int]
) -> List[UUID]:
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
        QueryString(
            {
                "not_statuses": "archived,error",
                "sort[id]": "desc",
                "dataset_ids": str(dataset_id),
            }
        ),
    )
    assert isinstance(response, dict)
    uuids = [UUID(uuid) for uuid in response["item_ids"]]
    return uuids


def get_item_ids_stage(
    api_client: ClientCore,
    team_slug: str,
    dataset_id: Union[int, str],
    stage_id: Union[UUID, str],
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
        QueryString(
            {"workflow_stage_ids": str(stage_id), "dataset_ids": str(dataset_id)}
        ),
    )
    assert isinstance(response, dict)
    uuids = [UUID(uuid) for uuid in response["item_ids"]]
    return uuids

def get_item(
    api_client: ClientCore, team_slug: str, item_id: Union[UUID, str], params: Optional[QueryString] = None
) -> Item:
    """
    Returns an item

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to get item ids for
    item_id: str
        The id or slug of the item to get

    Returns
    -------
    dict
        The item
    """
    if params is None:
        params = QueryString({})
    response = api_client.get(f"/v2/teams/{team_slug}/items/{item_id}", params)
    assert isinstance(response, dict)
    return parse_obj_as(Item, response)

def list_items(
    api_client: ClientCore,
    team_slug: str,
    params: QueryString,
) -> List[Item]:
    """
    Returns a list of items for the dataset

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to get items for
    dataset_id: str
        The id or slug of the dataset to get items for

    Returns
    -------
    List[Item]
        A list of items
    """
    response = api_client.get(
        f"/v2/teams/{team_slug}/items",
        params,
    )
    assert isinstance(response, dict)
    return parse_obj_as(List[Item], response["items"])