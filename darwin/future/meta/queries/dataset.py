import sys

from typing import Any, Dict, List

from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.datasets.get_dataset import get_dataset
from darwin.future.core.client import Client
from darwin.future.core.types.query import Query, QueryFilter
from darwin.future.data_objects.dataset import Dataset
from darwin.future.exceptions import DarwinException

from rich.console import Console

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
            raise DarwinException.from_exception(sys.last_value)

        if not self.filters:
            return datasets

        for filter in self.filters:
            datasets = self._execute_filter(datasets, filter)
        return datasets

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
        # TODO THIS IS JUST AN EXAMPLE - POPULATE WITH REAL LOGIC
        if filter.name == "dataset_type":
            return [d for d in datasets if filter.filter_attr(d.dataset_type.value)]
        else:
            return super()._generic_execute_filter(datasets, filter)
