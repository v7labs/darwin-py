from typing import List

from darwin.future.core.client import Client
from darwin.future.core.datasets.list_datasets import list_datasets
from darwin.future.core.types.query import Modifier, Param, Query, QueryFilter
from darwin.future.data_objects.dataset import Dataset
from darwin.future.data_objects.release import ReleaseList


class DatasetQuery(Query[Dataset]):
    """
    DatasetQuery object with methods to manage filters, retrieve data, and execute
    filters

    Methods
    -------

    where: Adds a filter to the query
    collect: Executes the query and returns the filtered data
    """

    def where(self, param: Param) -> "DatasetQuery":
        filter = QueryFilter.parse_obj(param)
        query = self + filter

        return DatasetQuery(query.filters)

    def collect(self, client: Client) -> List[Dataset]:
        datasets, exceptions = list_datasets(client)
        if exceptions:
            # TODO: print and or raise exceptions, tbd how we want to handle this
            pass

        if not self.filters:
            return datasets

        for filter in self.filters:
            datasets = self._execute_filters(datasets, filter)

        return datasets

    def _execute_filters(self, datasets: List[Dataset], filter: QueryFilter) -> List[Dataset]:
        """Executes filtering on the local list of datasets, applying special logic for role filtering
        otherwise calls the parent method for general filtering on the values of the datasets

        Parameters
        ----------
        datasets : List[Dataset]
        filter : QueryFilter

        Returns
        -------
        List[Dataset]: Filtered subset of datasets
        """

        if filter.name == "releases":
            return [d for d in datasets if d.releases and filter.param in [str(r) for r in d.releases]]

        return super()._generic_execute_filter(datasets, filter)
