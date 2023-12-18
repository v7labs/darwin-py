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
    assert isinstance(response, dict)
    return DatasetCore.model_validate(response)
