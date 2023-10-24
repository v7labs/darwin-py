import string

from pytest import mark, raises
from requests import HTTPError
from responses import RequestsMock

from darwin.future.core.client import DarwinConfig
from darwin.future.meta.client import Client
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.meta.objects.fixtures import *

# `datasets` tests
# TODO datasets tests

# `get_dataset_by_id` tests
# TODO get_dataset_by_id tests


# `create_dataset` tests
def test_create_dataset_raises_HTTPError(base_config: DarwinConfig) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps, raises(HTTPError):
        rsps.add(rsps.POST, base_url, status=500)
        Dataset.create_dataset(valid_client, valid_slug)


def test_create_dataset_returns_dataset_created_if_dataset_created(
    base_config: DarwinConfig,
) -> None:
    valid_client = Client(base_config)
    valid_slug = "test_dataset"

    base_url = base_config.base_url + "api/datasets"

    with RequestsMock() as rsps:
        rsps.add(
            rsps.POST,
            base_url,
            json={"id": 1, "name": "Test Dataset", "slug": "test_dataset"},
            status=201,
        )

        dataset_created = Dataset.create_dataset(valid_client, valid_slug)

        assert dataset_created is not None
        assert dataset_created.id == 1
        assert dataset_created.name == "test dataset"
        assert dataset_created.slug == "test_dataset"


# `update_dataset` tests
# TODO update_dataset tests


@mark.parametrize(
    "invalid_slug",
    [
        "",
        " ",
        "test dataset",
        *[f"dataset_{c}" for c in string.punctuation if c not in ["-", "_", "."]],
    ],
)
def test_validate_slugh_raises_exception_if_passed_invalid_inputs(
    invalid_slug: str,
) -> None:
    with raises(AssertionError):
        Dataset._validate_slug(invalid_slug)


def test_validate_slug_returns_none_if_passed_valid_slug() -> None:
    valid_slug = "test-dataset"

    assert Dataset._validate_slug(valid_slug) is None


def test_delete(base_meta_dataset: Dataset, base_config: DarwinConfig) -> None:
    base_url = base_config.base_url + "api/datasets"
    with RequestsMock() as rsps:
        rsps.add(
            rsps.PUT,
            base_url + f"/{base_meta_dataset.id}/archive",
            json={
                "id": base_meta_dataset.id,
                "name": "Test Dataset",
                "slug": "test_dataset",
            },
            status=200,
        )
        dataset_deleted = base_meta_dataset.delete()

        assert dataset_deleted == 1


def test_dataset_str_method(base_meta_dataset: Dataset) -> None:
    assert (
        base_meta_dataset.__str__()
        == "Dataset\n\
- Name: test dataset\n\
- Dataset Slug: test-dataset\n\
- Dataset ID: 1\n\
- Dataset Releases: No releases"
    )


def test_dataset_repr_method(base_meta_dataset: Dataset) -> None:
    assert base_meta_dataset.__repr__() == str(base_meta_dataset)
