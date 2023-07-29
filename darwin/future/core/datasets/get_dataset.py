from pydantic import parse_obj_as

from darwin.future.core.client import CoreClient
from darwin.future.core.types.common import QueryString
from darwin.future.data_objects.dataset import DatasetModel


def get_dataset(api_client: CoreClient, dataset_id: str) -> DatasetModel:
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

    return parse_obj_as(DatasetModel, response)
