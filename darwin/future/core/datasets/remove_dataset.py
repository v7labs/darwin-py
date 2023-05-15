from darwin.future.core.client import Client, JSONType
from darwin.future.core.types.common import QueryString


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
    response = api_client.delete(
        "/datasets",
        QueryString(
            {
                "name": name,
            }
        ),
    )

    return response
