from pydantic import parse_obj_as

from darwin.future.core.client import Client
from darwin.future.core.types import TeamSlug
from darwin.future.data_objects.dataset import Dataset


def create_dataset(api_client: Client, name: str) -> Dataset:
    ...
