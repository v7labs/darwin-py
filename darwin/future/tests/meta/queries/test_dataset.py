import responses
from pytest import fixture, mark

from darwin.future.core.client import Client
from darwin.future.data_objects.dataset import Dataset
from darwin.future.meta.objects.dataset import DatasetMeta
from darwin.future.meta.queries.dataset import DatasetQuery
from darwin.future.tests.core.fixtures import *


def test_dataset_collects_basic(base_client: Client, base_datasets_json: dict) -> None:
    query = DatasetQuery(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query.collect()
        assert len(datasets) == 2
        assert all([isinstance(dataset, DatasetMeta) for dataset in datasets])


def test_datasetquery_only_passes_back_correctly_formed_objects(base_client: Client, base_dataset_json: dict) -> None:
    query = DatasetQuery(base_client)
    with responses.RequestsMock() as rsps:
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=[base_dataset_json, {}])
        datasets = query.collect()

        assert len(datasets) == 1
        assert isinstance(datasets[0], DatasetMeta)


def test_dataset_filters_name(base_client: Client, base_datasets_json: dict) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where({"name": "name", "param": "test dataset 1"})
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query.collect()

        assert len(datasets) == 1
        assert datasets[0]._item is not None
        assert datasets[0]._item.slug == "test-dataset-1"


def test_dataset_filters_id(base_client: Client, base_datasets_json: dict) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where({"name": "id", "param": 1})
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query.collect()

        assert len(datasets) == 1
        assert datasets[0]._item is not None
        assert datasets[0]._item.slug == "test-dataset-1"


def test_dataset_filters_slug(base_client: Client, base_datasets_json: dict) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where({"name": "slug", "param": "test-dataset-1"})
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json)
        datasets = query.collect()

        assert len(datasets) == 1
        assert datasets[0]._item is not None
        assert datasets[0]._item.slug == "test-dataset-1"


def test_dataset_filters_releases(base_client: Client, base_datasets_json_with_releases: dict) -> None:
    with responses.RequestsMock() as rsps:
        query = DatasetQuery(base_client).where({"name": "releases", "param": "release1"})
        endpoint = base_client.config.api_endpoint + "datasets"
        rsps.add(responses.GET, endpoint, json=base_datasets_json_with_releases)

        datasets_odd_ids = query.collect()

        assert len(datasets_odd_ids) == 2
        assert datasets_odd_ids[0]._item is not None
        assert datasets_odd_ids[1]._item is not None
        assert datasets_odd_ids[0]._item.slug == "test-dataset-1"
        assert datasets_odd_ids[1]._item.slug == "test-dataset-3"

        query2 = DatasetQuery(base_client).where({"name": "releases", "param": "release2"})
        datasets_even_ids = query2.collect()

        assert len(datasets_even_ids) == 2
        assert datasets_even_ids[0]._item is not None
        assert datasets_even_ids[1]._item is not None
        assert datasets_even_ids[0]._item.slug == "test-dataset-2"
        assert datasets_even_ids[1]._item.slug == "test-dataset-4"
