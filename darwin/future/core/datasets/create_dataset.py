from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.data_objects.dataset import Dataset


def create_dataset(api_client: Client, name: str) -> Dataset:
    """
    Creates a new dataset for the given team

    Parameters
    ----------

    api_client: Client
        The client to use to make the request
    name: str
        The name of the dataset to create

    Returns
    -------
    Dataset
        The created dataset

    Raises
    ------
    HTTPError
        Any HTTP errors returned by the API
    """
    response = api_client.post(
        "/datasets",
        {
            "name": name,
        },
    )

    return parse_obj_as(Dataset, response)
