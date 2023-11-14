from pydantic import parse_obj_as

from darwin.future.core.client import ClientCore
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.dataset import DatasetCore


def get_dataset(api_client: ClientCore, dataset_id: str) -> DatasetCore:
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
    Dataset

    Raises
    ------
    HTTPError
        Any errors that occurred while making the request
    ValidationError
        Any errors that occurred while parsing the response
    """

    response = api_client.get("/datasets", QueryString({"id": str(dataset_id)}))

    return parse_obj_as(DatasetCore, response)


def get_dataset_by_slug(api_client: ClientCore, team_slug: str, dataset_slug: str) -> DatasetCore:
    """
    Returns a list of datasets for the given team

    Parameters
    ----------
    api_client : Client
        The client to use to make the request
    team_slug : str
        The slug of the team to retrieve the dataset from
    dataset_slug : str
        The slug of the dataset to retrieve

    Returns
    -------
    Dataset

    Raises
    ------
    HTTPError
        Any errors that occurred while making the request
    ValidationError
        Any errors that occurred while parsing the response
    """

    response = api_client.get(f"/{team_slug}/datasets", QueryString({"slug": dataset_slug}))

    return parse_obj_as(DatasetCore, response)
