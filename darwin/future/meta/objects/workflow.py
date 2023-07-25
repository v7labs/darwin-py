from __future__ import annotations

from enum import auto
from pathlib import Path
from typing import List, Optional, Sequence, Union
from uuid import UUID

from darwin.cli_functions import upload_data
from darwin.dataset.upload_manager import LocalFile
from darwin.datatypes import PathLike
from darwin.future.data_objects.workflow import WFDataset, WFType, Workflow
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery


class WorkflowMeta(MetaBase[Workflow]):
    @property
    def stages(self) -> StageQuery:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        meta_params = self.meta_params.copy()
        meta_params["workflow_id"] = self._item.id
        if self.datasets is not None:
            meta_params["dataset_id"] = self.datasets[0].id
            meta_params["dataset_name"] = self.datasets[0].name
        return StageQuery(self.client, meta_params=meta_params)

    @property
    def datasets(self) -> List[WFDataset]:
        if self._item is None:
            raise ValueError("WorkflowMeta has no item")
        if self._item.dataset is None:
            raise ValueError("WorkflowMeta has no associated dataset")
        return [self._item.dataset]

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

    def push_from_dataset_stage(self) -> WorkflowMeta:
        assert self._item is not None
        assert self._item.dataset is not None
        stages = self.stages
        ds_stage = stages[0]
        assert len(stages) > 1
        assert ds_stage._item is not None and ds_stage._item.type == WFType.DATASET
        next_stage = ds_stage._item.edges[0].target_stage_id
        assert next_stage is not None
        ds_stage.move_attached_files_to_stage(next_stage)
        return self

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
        auto_push: bool = True,
    ) -> WorkflowMeta:
        assert self._item is not None
        assert self._item.dataset is not None
        upload_data(
            self.datasets[0].name, files, files_to_exclude, fps, path, frames, extract_views, preserve_folders, verbose
        )
        if auto_push:
            self.push_from_dataset_stage()
        return self
