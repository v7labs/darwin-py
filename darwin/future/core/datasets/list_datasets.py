from typing import Optional

from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.core.types import TeamSlug
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.dataset import Dataset, DatasetList


def list_datasets(api_client: Client, team_slug: Optional[TeamSlug] = None) -> DatasetList:
    """
    Returns a list of datasets for the given team

    Parameters
    ----------
    api_client : Client
        The client to use to make the request
    team_slug : Optional[TeamSlug]
        The slug of the team to retrieve datasets for

    Returns
    -------
    DatasetList

    Raises
    ------
    HTTPError
        Any errors that occurred while making the request
    ValidationError
        Any errors that occurred while parsing the response

    """
    response = (
        api_client.get("/datasets", QueryString({"team": str(team_slug)})) if team_slug else api_client.get("/datasets")
    )

    return parse_obj_as(DatasetList, response)
