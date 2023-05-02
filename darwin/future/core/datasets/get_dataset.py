from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.core.types import TeamSlug
from darwin.future.data_objects.dataset import Dataset, DatasetList


def get_dataset(api_client: Client) -> DatasetList:
    """
    Returns a list of datasets for the given team
    """
    response = api_client.get("/datasets")

    return parse_obj_as(DatasetList, response)
