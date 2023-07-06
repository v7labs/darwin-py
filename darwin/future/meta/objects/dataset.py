from typing import List, Optional, Tuple, Union

from darwin.future.core.client import Client
from darwin.future.core.datasets.create_dataset import create_dataset
from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.datasets.remove_dataset import remove_dataset
from darwin.future.data_objects.dataset import Dataset
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase


class DatasetMeta(MetaBase[Dataset]):
    """Dataset Meta object. Facilitates the creation of Query objects, lazy loading of sub fields

    Args:
        MetaBase (Dataset): Generic MetaBase object expanded by Dataset core object return type

    Returns:
        _type_: DatasetMeta
    """

    client: Client

    def __init__(self, client: Client, datasets: Optional[List[Dataset]] = None) -> None:
        # TODO: Initialise from chaining within Client
        self.client = client
        super().__init__(datasets)

    def get_dataset_by_id(self) -> Dataset:
        # TODO: implement
        raise NotImplementedError()

    def create_dataset(self, slug: str) -> Tuple[Optional[List[Exception]], Optional[Dataset]]:
        """
        Creates a new dataset for the given team

        Parameters
        ----------
        slug: str [a-b0-9-_]
            The slug of the dataset to create

        Returns
        -------
        Tuple[Optional[List[Exception]], Optional[Dataset]]
            A tuple containing a list of exceptions and the dataset created

        """
        exceptions = []
        dataset: Optional[Dataset] = None

        try:
            self._validate_slug(slug)
            dataset = create_dataset(self.client, slug)
        except Exception as e:
            exceptions.append(e)

        return exceptions or None, dataset

    def update_dataset(self) -> Dataset:
        # TODO: implement in IO-1018
        raise NotImplementedError()

    def delete_dataset(self, dataset_id: Union[int, str]) -> Tuple[Optional[List[Exception]], int]:
        """
        Deletes a dataset by id or slug

        Parameters
        ----------
        dataset_id: Union[int, str]
            The id or slug of the dataset to delete

        Returns
        -------
        Tuple[Optional[List[Exception]], int]
            A tuple containing a list of exceptions and the number of datasets deleted
        """
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
        """
        (internal) Deletes a dataset by slug

        Parameters
        ----------
        client: MetaClient
            The client to use to make the request

        slug: str
            The slug of the dataset to delete

        Returns
        -------
        int
            The dataset deleted
        """
        assert_is(isinstance(client, Client), "client must be a Core Client")
        assert_is(isinstance(slug, str), "slug must be a string")

        dataset = get_dataset(client, slug)
        if dataset and dataset.id:
            dataset_deleted = remove_dataset(client, dataset.id)
        else:
            raise Exception(f"Dataset with slug {slug} not found")

        return dataset_deleted

    @staticmethod
    def _delete_by_id(client: Client, dataset_id: int) -> int:
        """
        (internal) Deletes a dataset by id

        Parameters
        ----------
        client: Client
            The client to use to make the request

        dataset_id: int
            The id of the dataset to delete

        Returns
        -------
        int
            The dataset deleted
        """
        assert_is(isinstance(client, Client), "client must be a Client")
        assert_is(isinstance(dataset_id, int), "dataset_id must be an integer")

        dataset_deleted = remove_dataset(client, dataset_id)
        return dataset_deleted

    @staticmethod
    def _validate_slug(slug: str) -> None:
        """
        Validates a slug

        Parameters
        ----------
        slug: str
            The slug to validate

        Raises
        ------
        AssertionError
        """
        slug_copy = str(slug).lower().strip()
        assert_is(isinstance(slug_copy, str), "slug must be a string")
        assert_is(len(slug_copy) > 0, "slug must not be empty")

        VALID_SLUG_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789-_"
        assert_is(all(c in VALID_SLUG_CHARS for c in slug_copy), "slug must only contain valid characters")

    def __next__(self) -> Dataset:
        if self._items is None:
            items, exceptions = list_datasets(self.client)
            self._items = items
        return super().__next__()
