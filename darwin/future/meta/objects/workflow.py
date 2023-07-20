from uuid import UUID

from darwin.future.core.items.move_items import move_items_to_stage
from darwin.future.data_objects.workflow import WFDataset, Workflow
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery


class WorkflowMeta(MetaBase[Workflow]):
    @property
    def stages(self) -> StageQuery:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        meta_params = self.meta_params.copy()
        meta_params["workflow_id"] = self._item.id
        if self.dataset is not None:
            meta_params["dataset_id"] = self.dataset.id
            meta_params["dataset_name"] = self.dataset.name
        return StageQuery(self.client, meta_params=meta_params)

    @property
    def dataset(self) -> WFDataset:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        if self._item.dataset is None:
            raise ValueError("WorkflowMeta has no associated dataset")
        return self._item.dataset

    @property
    def id(self) -> UUID:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        return self._item.id

    @property
    def name(self) -> str:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        return self._item.name

    def push_from_dataset_stage(self) -> None:
        assert self._item is not None
        assert self._item.dataset is not None
        stages = self.stages
        assert len(stages) > 1
        ds_stage = stages[0]
        item_ids = ds_stage.item_ids
        assert ds_stage._item is not None
        next_stage = ds_stage._item.edges[0].target_stage_id
        assert next_stage is not None
        slug, d_id, w_id = self.meta_params["team_slug"], self._item.dataset.id, self._item.id
        move_items_to_stage(self.client, str(slug), w_id, d_id, next_stage, item_ids)
