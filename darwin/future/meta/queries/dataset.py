from typing import Any, Dict, List

from darwin.future.core.client import Client
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.types.query import Query, QueryFilter
from darwin.future.data_objects.dataset import Dataset, DatasetList
from darwin.future.exceptions.base import DarwinException
from darwin.future.helpers.pretty_exception import pretty_exception

Param = Dict[str, Any]  # type: ignore


class DatasetQuery(Query[Dataset]):
    """DatasetQuery object with methods to manage filters, retrieve data, and execute filters
    Methods:
    where: Adds a filter to the query
    collect: Executes the query and returns the filtered data
    _execute_filter: Executes a filter on a list of objects
    """

    @staticmethod
    def by_id(client: Client, id: int) -> Dataset:
        output = DatasetQuery([QueryFilter(name="id", param=str(id))]).collect(client)
        if len(output) == 1:
            return output[0]
        else:
            raise DarwinException(f"Dataset with id {id} not found")

    @staticmethod
    def by_name(client: Client, name: str) -> Dataset:
        output = DatasetQuery([QueryFilter(name="name", param=name)]).collect(client)
        if len(output) == 1:
            return output[0]
        else:
            raise DarwinException(f"Dataset with name {name} not found")

    def where(self, param: Param) -> "DatasetQuery":
        filter = QueryFilter.parse_obj(param)
        query = self + filter
        return DatasetQuery(query.filters)

    def collect(self, client: Client) -> List[Dataset]:
        try:
            datasets = list_datasets(client)
        except Exception:
            datasets = []
            pretty_exception()

        if not self.filters:
            return datasets

        for filter in self.filters:
            datasets = self._execute_filter(datasets, filter)
        return datasets

    def _id_filter(self, datasets: DatasetList, filter: QueryFilter) -> DatasetList:
        # In place to prevent operator matching by the filter_attr method.
        return [dataset for dataset in datasets if filter.filter_attr(dataset.id)]

    def _releases_filter(self, datasets: DatasetList, filter: QueryFilter) -> DatasetList:
        datasets_for_return: DatasetList = []

        for dataset in datasets:
            if filter.filter_attr(dataset.releases):
                datasets_for_return.append(dataset)

        return datasets_for_return

    filterables: List[str] = ["id", "releases"]

    def _execute_filter(self, datasets: List[Dataset], filter: QueryFilter) -> List[Dataset]:
        """Executes filtering on the local list of datasets, applying special logic for dataset_type filtering
        otherwise calls the parent method for general filtering on the values of the datasets

        Parameters
        ----------
        datasets : List[Dataset]
        filter : QueryFilter

        Returns
        -------
        List[Dataset]: Filtered subset of datasets
        """
        if filter.name in self.filterables:
            filter_func = getattr(self, f"_{filter.name}_filter")

            if not callable(filter_func):
                raise DarwinException(f"Filtering on {filter.name} is not supported")

            return filter_func(datasets, filter)
        else:
            return super()._generic_execute_filter(datasets, filter)
