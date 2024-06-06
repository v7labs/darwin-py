from __future__ import annotations

from typing import List, Literal, Tuple, Union
from uuid import UUID

from pydantic import ValidationError

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import JSONDict, QueryString
from darwin.future.data_objects.item import Folder, ItemCore


def get_item_ids(
    api_client: ClientCore,
    team_slug: str,
    dataset_id: Union[str, int],
    params: QueryString = QueryString({}),
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
        f"/v2/teams/{team_slug}/items/list_ids",
        QueryString(
            {
                "dataset_ids": str(dataset_id),
            }
        )
        + params,
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
    api_client: ClientCore,
    team_slug: str,
    item_id: Union[UUID, str],
    params: QueryString = QueryString({}),
) -> ItemCore:
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
    Item
        An item object
    """
    response = api_client.get(f"/v2/teams/{team_slug}/items/{item_id}", params)
    assert isinstance(response, dict)
    return ItemCore.model_validate(response)


def list_items(
    api_client: ClientCore,
    team_slug: str,
    dataset_ids: int | list[int] | Literal["all"],
    params: QueryString = QueryString({}),
) -> Tuple[List[ItemCore], List[ValidationError]]:
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
    List[ValidationError]
        A list of ValidationError on failed objects
    """
    dataset_ids = (
        dataset_ids
        if isinstance(dataset_ids, list) or dataset_ids == "all"
        else [dataset_ids]
    )
    params = params + QueryString({"dataset_ids": dataset_ids})
    response = api_client.get(f"/v2/teams/{team_slug}/items", params)
    assert isinstance(response, dict)
    items: List[ItemCore] = []
    exceptions: List[ValidationError] = []
    for item in response["items"]:
        assert isinstance(item, dict)
        try:
            items.append(ItemCore.model_validate(item))
        except ValidationError as e:
            exceptions.append(e)
    return items, exceptions


def list_folders(
    api_client: ClientCore,
    team_slug: str,
    params: QueryString,
) -> Tuple[List[Folder], List[ValidationError]]:
    """
    Returns a list of folders for the team and dataset

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to get folder ids for
    params: QueryString
        parameters to filter the folders

    Returns
    -------
    List[Folder]
        The folders
    List[ValidationError]
        A list of ValidationError on failed objects
    """
    assert "dataset_ids" in params.value, "dataset_ids must be provided"
    response = api_client.get(f"/v2/teams/{team_slug}/items/folders", params)
    assert isinstance(response, dict)
    assert "folders" in response
    exceptions: List[ValidationError] = []
    folders: List[Folder] = []
    for item in response["folders"]:
        try:
            folders.append(Folder.model_validate(item))
        except ValidationError as e:
            exceptions.append(e)
    return folders, exceptions


def list_items_unstable(
    api_client: ClientCore,
    team_slug: str,
    params: JSONDict,
) -> Tuple[List[ItemCore], List[ValidationError]]:
    """
    Returns a list of items for the dataset from the advanced filters 'unstable' endpoint

    Parameters
    ----------
    client: Client
        The client to use for the request
    team_slug: str
        The slug of the team to get items for
    params: JSONType
        Must include at least dataset_ids

    Returns
    -------
    List[Item]
        A list of items
    List[ValidationError]
        A list of ValidationError on failed objects
    """
    if "dataset_ids" not in params:
        raise ValueError("dataset_ids must be provided")
    response = api_client.post(f"/unstable/teams/{team_slug}/items/list", params)
    assert isinstance(response, dict)
    items: List[ItemCore] = []
    exceptions: List[ValidationError] = []
    for item in response["items"]:
        assert isinstance(item, dict)
        try:
            items.append(ItemCore.model_validate(item))
        except ValidationError as e:
            exceptions.append(e)
    return items, exceptions
