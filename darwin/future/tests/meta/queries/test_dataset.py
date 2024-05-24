import responses

from darwin.future.core.client import ClientCore
from darwin.future.meta.objects.dataset import Dataset
from darwin.future.meta.queries.dataset import DatasetQuery
from darwin.future.tests.core.fixtures import *


def test_dataset_collects_basic(
    base_client: ClientCore, base_datasets_json: dict
) -> None:
    query = DatasetQuery(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query._collect().values()
        assert len(datasets) == 2
        assert all(isinstance(dataset, Dataset) for dataset in datasets)


def test_datasetquery_only_passes_back_correctly_formed_objects(
    base_client: ClientCore, base_dataset_json: dict
) -> None:
    query = DatasetQuery(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=[base_dataset_json, {}])
        datasets = query._collect()

        assert len(datasets) == 1
        assert isinstance(datasets[0], Dataset)


def test_dataset_filters_name(
    base_client: ClientCore, base_datasets_json: dict
) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where(
            {"name": "name", "param": "test dataset 1"}
        )
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query._collect()

        assert len(datasets) == 1
        assert datasets[0]._element.slug == "test-dataset-1"


def test_dataset_filters_id(base_client: ClientCore, base_datasets_json: dict) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where({"name": "id", "param": 1})
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query._collect()

        assert len(datasets) == 1
        assert datasets[0]._element.slug == "test-dataset-1"


def test_dataset_filters_slug(
    base_client: ClientCore, base_datasets_json: dict
) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where(
            {"name": "slug", "param": "test-dataset-1"}
        )
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query._collect()

        assert len(datasets) == 1
        assert datasets[0]._element.slug == "test-dataset-1"


def test_dataset_filters_releases(
    base_client: ClientCore, base_datasets_json_with_releases: dict
) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where(
            {"name": "releases", "param": "release1"}
        )
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json_with_releases)

        datasets_odd_ids = query._collect()

        assert len(datasets_odd_ids) == 2
        assert datasets_odd_ids[0]._element.slug == "test-dataset-1"
        assert datasets_odd_ids[1]._element.slug == "test-dataset-3"

        query2 = DatasetQuery(base_client).where(
            {"name": "releases", "param": "release2"}
        )
        datasets_even_ids = query2._collect()

        assert len(datasets_even_ids) == 2
        assert datasets_even_ids[0]._element.slug == "test-dataset-2"
        assert datasets_even_ids[1]._element.slug == "test-dataset-4"
