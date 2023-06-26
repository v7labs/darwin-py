from typing import List, Optional, Tuple, Union

from darwin.future.core.client import Client
from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.datasets.remove_dataset import remove_dataset
from darwin.future.data_objects.dataset import Dataset
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase


class DatasetMeta(MetaBase[Dataset]):
    client: Client

    def __init__(self, client: Client, datasets: Optional[List[Dataset]]=None) -> None:
        # TODO: Initialise from chaining within MetaClient
        self.client = client
        super().__init__(datasets)
        

    def get_dataset_by_id(self) -> Dataset:
        # TODO: implement
        raise NotImplementedError()

    def create_dataset(self) -> Dataset:
        # TODO: implement in IO-1018
        raise NotImplementedError()

    def update_dataset(self) -> Dataset:
        # TODO: implement in IO-1018
        raise NotImplementedError()

    def delete_dataset(self, dataset_id: Union[int, str]) -> Tuple[Optional[List[Exception]], int]:
        exceptions = []
        dataset_deleted = -1

        try:
            if isinstance(dataset_id, str):
                dataset_deleted = self._delete_by_slug(self.client, dataset_id)
            else:
                dataset_deleted = self._delete_by_id(self.client, dataset_id)

        except Exception as e:
            exceptions.append(e)

        return exceptions or None, dataset_deleted

    @staticmethod
    def _delete_by_slug(client: Client, slug: str) -> int:
        assert_is(isinstance(client, Client), "client must be a MetaClient")
        assert_is(isinstance(slug, str), "slug must be a string")

        dataset = get_dataset(client, slug)
        if dataset and dataset.id:
            dataset_deleted = remove_dataset(client, dataset.id)
        else:
            raise Exception(f"Dataset with slug {slug} not found")

        return dataset_deleted

    @staticmethod
    def _delete_by_id(client: Client, dataset_id: int) -> int:
        assert_is(isinstance(client, Client), "client must be a MetaClient")
        assert_is(isinstance(dataset_id, int), "dataset_id must be an integer")

        dataset_deleted = remove_dataset(client, dataset_id)
        return dataset_deleted


    def __next__(self) -> Dataset:
        if self._items is None:
            items, exceptions = list_datasets(self.client)
            self._items = items
        return super().__next__()