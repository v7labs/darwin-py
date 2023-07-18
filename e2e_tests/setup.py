import random
import string
from dataclasses import dataclass
from typing import List, Literal

import pytest
import requests

from e2e_tests.conftest import ConfigValues
from e2e_tests.exceptions import E2EException


# Datastructures to store minimal info about the created datasets and items
@dataclass
class E2EItem(Exception):
    name: str
    # TODO: Add more fields


@dataclass
class E2EDataset:
    id: int
    name: str
    items: List[E2EItem] = []

    def add_item(self, item: E2EItem) -> None:
        self.items.append(item)


@dataclass
class E2ETestRunInfo:
    prefix: str
    datasets: List[E2EDataset]


def api_call(verb: Literal["get", "post", "put", "delete"], url: str, payload: dict, api_key: str) -> requests.Response:
    """
    Make an API call to the server
    (Written independently of the client library to avoid relying on tested items)

    Parameters
    ----------
    verb : Literal["get", "post", "put" "delete"]
        The HTTP verb to use
    url : str
        The URL to call
    payload : dict
        The payload to send
    api_key : str
        The API key to use

    Returns
    -------
    requests.Response
        The response object
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    action = getattr(requests, verb)

    response = action(url, headers=headers, json=payload)
    return response


alphabet = string.ascii_lowercase + string.digits


def generate_random_string(length: int = 6) -> str:
    """
    A random-enough to avoid collision on test runs prefix generator

    Parameters
    ----------
    length : int
        The length of the prefix to generate

    Returns
    -------
    str
        The generated prefix, of length (length).  Matches [a-z0-9]
    """
    return "".join(random.choice(alphabet) for i in range(length))


# ! Untested
def create_dataset(prefix: str, config: ConfigValues) -> E2EDataset:
    """
    Create a randomised new dataset, and return its minimal info for reference

    Parameters
    ----------
    prefix : str
        The prefix to use for the dataset name
    config : ConfigValues
        The config values to use

    Returns
    -------
    E2EDataset
        The minimal info about the created dataset
    """
    name = f"{prefix}_{generate_random_string(4)}_dataset"
    host, api_key = config.server, config.api_key
    url = f"{host}/api/v1/datasets"

    try:
        response = api_call("post", url, {"name": name}, api_key)

        if response.ok:
            dataset_info = response.json()
            return E2EDataset(id=dataset_info["id"], name=dataset_info["name"])

        raise E2EException(f"Failed to create dataset {name} - {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to create dataset {name} - {e}")
        pytest.exit("Test run failed in test setup stage")


# ! Untested
def create_item(dataset_slug: str, prefix: str, config: ConfigValues) -> E2EItem:
    """
    Creates a randomised new item, and return its minimal info for reference

    Parameters
    ----------
    prefix : str
        The prefix to use for the item name
    config : ConfigValues
        The config values to use

    Returns
    -------
    E2EItem
        The minimal info about the created item
    """
    name = f"{prefix}_{generate_random_string(4)}_item"
    host, api_key = config.server, config.api_key
    url = f"{host}/api/v1/datasets/{dataset_slug}/items"

    try:
        response = api_call("post", url, {"name": name}, api_key)

        if response.ok:
            # ! needs replacing
            item_info = response.json()
            return E2EItem(name=item_info["name"])

        raise E2EException(f"Failed to create dataset {name} - {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Failed to create dataset {name} - {e}")
        pytest.exit("Test run failed in test setup stage")


def setup(config: ConfigValues) -> List[E2EDataset]:
    """
    Setup data for End to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use

    Returns
    -------
    List[E2EDataset]
        The minimal info about the created datasets
    """
    number_of_datasets = 3
    number_of_items = 0

    datasets: List[E2EDataset] = []

    try:
        prefix = generate_random_string()
        for _ in range(number_of_datasets):
            dataset = create_dataset(prefix, config)
            for _ in range(number_of_items):
                item = create_item(dataset.name, prefix, config)

                dataset.add_item(item)

    except E2EException as e:
        print(e)
        pytest.exit("Test run failed in test setup stage")

    except Exception as e:
        print(e)
        pytest.exit("Setup failed - unknown error")

    return datasets


def teardown(config: ConfigValues, datasets: List[E2EDataset]) -> None:
    """
    Teardown data for End to end test runs

    Parameters
    ----------
    config : ConfigValues
        The config values to use
    datasets : List[E2EDataset]
        The minimal info about the created datasets
    """
    host, api_key = config.server, config.api_key

    for dataset in datasets:
        url = f"{host}/api/v1/datasets/{dataset.id}"
        response = api_call("delete", url, {}, api_key)

        if not response.ok:
            print(f"Failed to delete dataset {dataset.name} - {response.status_code} - {response.text}")
