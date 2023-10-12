from __future__ import annotations

from typing import List

from darwin.future.core.datasets import list_datasets
from darwin.future.core.types.query import Param, Query, QueryFilter
from darwin.future.meta.objects.dataset import Dataset


class DatasetQuery(Query[Dataset]):
    """
    DatasetQuery object with methods to manage filters, retrieve data, and execute
    filters

    Methods
    -------

    collect: Executes the query and returns the filtered data
    """

    def _collect(self) -> List[Dataset]:
        datasets, exceptions = list_datasets(self.client)
        if exceptions:
            # TODO: print and or raise exceptions, tbd how we want to handle this
            pass
        datasets_meta = [Dataset(self.client, dataset) for dataset in datasets]
        if not self.filters:
            self.filters = []

        for filter in self.filters:
            datasets_meta = self._execute_filters(datasets_meta, filter)

        return datasets_meta

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
            return [
                d
                for d in datasets
                if d._element is not None
                and d._element.releases
                and filter.param in [str(r) for r in d._element.releases]
            ]

        return super()._generic_execute_filter(datasets, filter)
