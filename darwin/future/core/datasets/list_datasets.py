from typing import List, Tuple

from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.data_objects.dataset import Dataset


def list_datasets(api_client: Client) -> Tuple[List[Dataset], List[Exception]]:
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
    Tuple[DatasetList, List[Exception]]
    """
    datasets: List[Dataset] = []
    errors: List[Exception] = []

    try:
        response = api_client.get("/datasets")
        for item in response:
            datasets.append(parse_obj_as(Dataset, item))
    except Exception as e:
        errors.append(e)

    return datasets, errors
