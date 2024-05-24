from typing import Optional

from darwin.future.core.client import ClientCore
from darwin.future.exceptions import DatasetNotFound


def remove_dataset(
    api_client: ClientCore, id: int, team_slug: Optional[str] = None
) -> int:
    """
    Creates a new dataset for the given team

    Parameters
    ----------
    api_client : Client
        The client to use to make the request
    id : int
        The name of the dataset to create
    team_slug : str
        The slug of the team to create the dataset in

    Returns
    -------
    int
        The dataset deleted id
    """
    if not team_slug:
        team_slug = api_client.config.default_team

    response = api_client.put(
        f"/datasets/{id}/archive",
        {"team_slug": team_slug},
    )
    assert isinstance(response, dict)

    if "id" not in response:
        raise DatasetNotFound(f"Dataset with id {id} not found")

    return int(response["id"])
