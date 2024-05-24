from darwin.future.core.client import ClientCore
from darwin.future.data_objects.dataset import DatasetCore


def create_dataset(api_client: ClientCore, name: str) -> DatasetCore:
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
    assert isinstance(response, dict)
    return DatasetCore.model_validate(response)
