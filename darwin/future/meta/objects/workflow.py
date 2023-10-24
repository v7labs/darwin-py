from __future__ import annotations

import logging
from typing import List, Optional, Sequence, Union
from uuid import UUID

from darwin.cli_functions import _load_client
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.dataset.upload_manager import LocalFile, UploadHandler
from darwin.datatypes import PathLike
from darwin.future.data_objects.workflow import WFDatasetCore, WFTypeCore, WorkflowCore
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.stage import StageQuery

logger = logging.getLogger(__name__)


class Workflow(MetaBase[WorkflowCore]):
    @property
    def stages(self) -> StageQuery:
        meta_params = self.meta_params.copy()
        meta_params["workflow_id"] = self._element.id
        if self.datasets is not None:
            meta_params["dataset_id"] = self.datasets[0].id
            meta_params["dataset_name"] = self.datasets[0].name
        return StageQuery(self.client, meta_params=meta_params)

    @property
    def datasets(self) -> List[WFDatasetCore]:
        if self._element.dataset is None:
            raise ValueError("WorkflowMeta has no associated dataset")
        return [self._element.dataset]

    @property
    def id(self) -> UUID:
        return self._element.id

    @property
    def name(self) -> str:
        return self._element.name

    def push_from_dataset_stage(self) -> Workflow:
        assert self._element.dataset is not None
        stages = self.stages
        ds_stage = stages[0]
        assert len(stages) > 1
        assert ds_stage._element.type == WFTypeCore.DATASET
        next_stage = ds_stage._element.edges[0].target_stage_id
        assert next_stage is not None
        ds_stage.move_attached_files_to_stage(next_stage)
        return self

    def upload_files(
        self,
        files: Sequence[Union[PathLike, LocalFile]],
        files_to_exclude: Optional[List[PathLike]] = None,
        fps: int = 1,
        path: Optional[str] = None,
        as_frames: bool = False,
        extract_views: bool = False,
        preserve_folders: bool = False,
        verbose: bool = False,
        auto_push: bool = True,
    ) -> UploadHandler:
        """ """

        assert self._element.dataset is not None
        if verbose:
            logger.warning(
                "Verbose is deprecated in more recent versions, feedback on uploads can be obtained from returned object"
            )

        wf_dataset: WFDatasetCore = self._element.dataset

        old_style_client = _load_client()
        old_style_dataset = old_style_client.get_remote_dataset(wf_dataset.name)

        assert isinstance(old_style_dataset, RemoteDatasetV2), "Only RemoteDatasetV2 is supported"

        handler = old_style_dataset.push(
            files,
            blocking=False,
            files_to_exclude=files_to_exclude,
            fps=fps,
            path=path,
            as_frames=as_frames,
            extract_views=extract_views,
            preserve_folders=preserve_folders,
        )

        # TODO: how do we handle autopush to next stage asynchrnously?

        return handler

        # if auto_push:
        #     self.push_from_dataset_stage()
        # return self

    # async def _async_push(
    #     self,
    #     dataset: WFDatasetCore,
    #     files: Sequence[Union[PathLike, LocalFile]],
    #     files_to_exclude: Optional[List[PathLike]] = None,
    #     fps: int = 1,
    #     as_frames: bool = False,
    #     extract_views: bool = False,
    #     path: Optional[str] = None,
    #     preserve_folders: bool = False,
    # ):
    #     assert self.client is not None
