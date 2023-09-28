from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union
from uuid import UUID

from darwin.cli_functions import upload_data
from darwin.dataset.upload_manager import LocalFile
from darwin.datatypes import PathLike
from darwin.future.core.client import ClientCore
from darwin.future.core.datasets import create_dataset, get_dataset, remove_dataset
from darwin.future.core.items import get_item_ids
from darwin.future.data_objects.dataset import DatasetCore
from darwin.future.exceptions import MissingDataset
from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.objects.base import MetaBase


class Dataset(MetaBase[DatasetCore]):
    """Dataset Meta object. Facilitates the creation of Query objects, lazy loading of sub fields

    Args:
        MetaBase (Dataset): Generic MetaBase object expanded by Dataset core object return type

    Returns:
        _type_: DatasetMeta
    """

    @property
    def name(self) -> str:
        assert self._element.name is not None
        return self._element.name

    @property
    def slug(self) -> str:
        assert self._element.slug is not None
        return self._element.slug

    @property
    def id(self) -> int:
        assert self._element.id is not None
        return self._element.id

    @property
    def item_ids(self) -> List[UUID]:
        """Returns a list of item ids for the dataset

        Returns:
            List[UUID]: A list of item ids
        """
        assert self._element.id is not None
        assert self.meta_params["team_slug"] is not None and type(self.meta_params["team_slug"]) == str
        return get_item_ids(self.client, self.meta_params["team_slug"], str(self._element.id))

    def get_dataset_by_id(self) -> DatasetCore:
        # TODO: implement
        raise NotImplementedError()

    @classmethod
    def create_dataset(cls, client: ClientCore, slug: str) -> Tuple[Optional[List[Exception]], Optional[DatasetCore]]:
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
        dataset: Optional[DatasetCore] = None

        try:
            cls._validate_slug(slug)
            dataset = create_dataset(client, slug)
        except Exception as e:
            exceptions.append(e)

        return exceptions or None, dataset

    def update_dataset(self) -> DatasetCore:
        # TODO: implement in IO-1018
        raise NotImplementedError()

    @classmethod
    def delete_dataset(cls, client: ClientCore, dataset_id: Union[int, str]) -> Tuple[Optional[List[Exception]], int]:
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
                dataset_deleted = cls._delete_by_slug(client, dataset_id)
            else:
                dataset_deleted = cls._delete_by_id(client, dataset_id)

        except Exception as e:
            exceptions.append(e)

        return exceptions or None, dataset_deleted

    @staticmethod
    def _delete_by_slug(client: ClientCore, slug: str) -> int:
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
        assert_is(isinstance(client, ClientCore), "client must be a Core Client")
        assert_is(isinstance(slug, str), "slug must be a string")

        dataset = get_dataset(client, slug)
        if dataset and dataset.id:
            dataset_deleted = remove_dataset(client, dataset.id)
        else:
            raise MissingDataset(f"Dataset with slug {slug} not found")

        return dataset_deleted

    @staticmethod
    def _delete_by_id(client: ClientCore, dataset_id: int) -> int:
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
        assert_is(isinstance(client, ClientCore), "client must be a Client")
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

    def upload_files(
        self,
        files: Sequence[Union[PathLike, LocalFile]],
        files_to_exclude: Optional[List[PathLike]] = None,
        fps: int = 1,
        path: Optional[str] = None,
        frames: bool = False,
        extract_views: bool = False,
        preserve_folders: bool = False,
        verbose: bool = False,
    ) -> Dataset:
        upload_data(
            self._element.name, files, files_to_exclude, fps, path, frames, extract_views, preserve_folders, verbose  # type: ignore
        )
        return self
