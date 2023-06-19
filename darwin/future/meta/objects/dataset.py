from typing import List, Optional, Tuple, Union

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
    def delete_dataset(cls, dataset_id: Union[int, str]) -> Tuple[Optional[List[Exception]], int]:
        exceptions = []
        dataset_deleted = 0

        try:
            # TODO: implement
            # 1. recover dataset if slug
            # 2. delete dataset
            # 3. assign int id to dataset_deleted
            ...
        except Exception as e:
            exceptions.append(e)

        return exceptions or None, dataset_deleted
