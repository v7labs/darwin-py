import random
import string
from dataclasses import dataclass
from typing import List, Literal

import Faker
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
    items: List[E2EItem]

    def add_item(self, item: E2EItem) -> None:
        self.items.append(item)


@dataclass
class E2ETestRunInfo:
    prefix: str
    datasets: List[E2EDataset]


def api_call(verb: Literal["get", "post", "put" "delete"], url: str, payload: dict, api_key: str) -> requests.Response:
    headers = {"Authorization": f"Bearer {api_key}"}
    action = getattr(requests, verb)

    response = action(url, headers=headers, json=payload)
    return response


alphabet = string.ascii_lowercase + string.digits


def generate_prefix(length: int = 6) -> str:
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


def create_dataset(prefix: str) -> E2EDataset:
    name = f"{prefix}_{faker}_dataset"


# TODO Create an item within the dataset for the tests to use
def create_item(prefix: str) -> E2EItem:
    ...


# TODO: Main setup orchestration
def setup(config: ConfigValues) -> List[E2EDataset]:
    number_of_datasets = 3
    number_of_items = 3

    datasets: List[E2EDataset] = []

    try:
        prefix = generate_prefix()
        for _ in range(number_of_datasets):
            dataset = create_dataset(prefix)
            for _ in range(number_of_items):
                item = create_item(prefix)

                dataset.add_item(item)

    except E2EException as e:
        print(e)
        pytest.exit("Test run failed in test setup stage")

    except Exception as e:
        print(e)
        pytest.exit("Setup failed - unknown error")

    return datasets
