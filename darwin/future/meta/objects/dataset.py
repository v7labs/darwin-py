from typing import Tuple, Union

from pydantic import PositiveInt
from torch import int16

from darwin.future.data_objects.dataset import Dataset
from darwin.future.meta.queries.dataset import DatasetQuery


class DatasetMeta:
    @classmethod
    def datasets(cls) -> DatasetQuery:
        # TODO: implement
        raise NotImplementedError()

    @classmethod
    def get_dataset_by_id(cls) -> Dataset:
        # TODO: implement
        raise NotImplementedError()

    @classmethod
    def create_dataset(cls) -> Dataset:
        # TODO: implement in IO-1018
        raise NotImplementedError()

    @classmethod
    def update_dataset(cls) -> Dataset:
        # TODO: implement in IO-1018
        raise NotImplementedError()

    @classmethod
    def delete_dataset(cls, dataset_id: Union[int, str]) -> Tuple[Exception, int]:
        # TODO: implement in IO-1019
        raise NotImplementedError()
