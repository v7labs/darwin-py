from pydantic import parse_obj_as
from requests import Response

from darwin.future.core.client import Client
from darwin.future.core.types.common import JSONType
from darwin.future.data_objects.dataset import Dataset


def remove_dataset(api_client: Client, name: str) -> JSONType:
    """
    Creates a new dataset for the given team

    Parameters
    ----------
    api_client : Client
        The client to use to make the request
    name : str
        The name of the dataset to create

    Returns
    -------
    Dataset
    """
    response: JSONType = api_client.delete(
        "/datasets",
        {
            "name": name,
        },
    )

    return response
