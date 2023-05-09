from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.core.types import TeamSlug
from darwin.future.data_objects.dataset import Dataset, DatasetList


def get_dataset(api_client: Client, dataset_id: str) -> DatasetList:
    """
    Returns a list of datasets for the given team

    Parameters
    ----------
    api_client : Client
        The client to use to make the request
    dataset_id : str
        The id of the dataset to retrieve

    Returns
    -------
    DatasetList

    Raises
    ------
    HTTPError
        Any errors that occurred while making the request
    """
    response = api_client.get("/datasets", {"team": TeamSlug(dataset_id).team_slug})  # TODO PICK UP HERE

    return parse_obj_as(DatasetList, response)
