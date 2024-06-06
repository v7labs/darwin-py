from typing import List, Tuple

from pydantic import ValidationError

from darwin.future.core.client import ClientCore
from darwin.future.data_objects.dataset import DatasetCore


def list_datasets(
    api_client: ClientCore,
) -> Tuple[List[DatasetCore], List[ValidationError]]:
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
    List[DatasetList]:
        A list of datasets
    List[ValidationError]
        A list of Validation errors on failed objects
    """
    datasets: List[DatasetCore] = []
    errors: List[ValidationError] = []

    response = api_client.get("/datasets")
    try:
        for item in response:
            assert isinstance(item, dict)
            datasets.append(DatasetCore.model_validate(item))
    except ValidationError as e:
        errors.append(e)

    return datasets, errors
