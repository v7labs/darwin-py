from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.core.types import TeamSlug
from darwin.future.data_objects.dataset import Dataset


def create_dataset(api_client: Client, name: str) -> Dataset:
    """
    Creates a new dataset for the given team
    """
    response = api_client.post(
        "/datasets",
        {
            "name": name,
        },
    )

    return parse_obj_as(Dataset, response)
