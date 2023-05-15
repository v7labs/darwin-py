from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.data_objects.dataset import DatasetList


def list_datasets(api_client: Client) -> DatasetList:
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
    response = api_client.get("/datasets")

    return parse_obj_as(DatasetList, response)
