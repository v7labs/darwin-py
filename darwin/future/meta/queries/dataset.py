import sys
from typing import Any, Callable, Dict, List

from rich.console import Console

from darwin.future.core.client import Client
from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.types.query import Query, QueryFilter
from darwin.future.data_objects.dataset import Dataset, DatasetList
from darwin.future.data_objects.release import Release, ReleaseList
from darwin.future.exceptions.base import DarwinException

Param = Dict[str, Any]  # type: ignore


class DatasetQuery(Query[Dataset]):
    """DatasetQuery object with methods to manage filters, retrieve data, and execute filters
    Methods:
    where: Adds a filter to the query
    collect: Executes the query and returns the filtered data
    _execute_filter: Executes a filter on a list of objects
    """

    def where(self, param: Param) -> "DatasetQuery":
        filter = QueryFilter.parse_obj(param)
        query = self + filter
        return DatasetQuery(query.filters)

    def collect(self, client: Client) -> List[Dataset]:
        try:
            datasets = list_datasets(client)
        except Exception:
            Console().print_exception()
            if (exc := sys.last_value) is not None:
                raise DarwinException.from_exception(exc)
            raise DarwinException("Unknown error occurred while collecting datasets")

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

    filterables: Dict[str, Callable] = {
        "id": _id_filter,
        "releases": _releases_filter,
    }

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
        if filter.name in self.filterables.keys():
            filter_func = self.filterables[filter.name]
            return filter_func(datasets, filter)
        else:
            return super()._generic_execute_filter(datasets, filter)
