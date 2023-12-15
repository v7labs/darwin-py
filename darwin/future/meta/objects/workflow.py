from __future__ import annotations

from typing import List, Optional, Sequence, Union
from uuid import UUID

from darwin.cli_functions import upload_data
from darwin.dataset.upload_manager import LocalFile
from darwin.datatypes import PathLike
from darwin.future.data_objects.workflow import WFDatasetCore, WFTypeCore, WorkflowCore
from darwin.future.exceptions import MissingDataset
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.item import ItemQuery
from darwin.future.meta.queries.stage import Stage, StageQuery


class Workflow(MetaBase[WorkflowCore]):
    """
    Workflow Meta object. Facilitates the creation of Query objects, lazy loading of
    sub fields

    Args:
        MetaBase (Workflow): Generic MetaBase object expanded by Workflow core object
            return type

    Returns:
        _type_: Workflow

    Attributes:
        name (str): The name of the workflow.
        id (UUID): The id of the workflow
        datasets (List[Dataset]): A list of datasets associated with the workflow.
        stages (StageQuery): Queries stages associated with the workflow.

    Methods:
        push_from_dataset_stage() -> Workflow:
            moves all items associated with the dataset stage to the next connected stage
        upload_files(...): -> Workflow:
            Uploads files to the dataset stage of the workflow

    Example Usage:
        # Get the workflow object
        workflow = client.team.workflows.where(name='test').collect_one()

        # Get the stages associated with the workflow
        stages = workflow.stages

        # Get the datasets associated with the workflow
        datasets = workflow.datasets
    """

    @property
    def items(self) -> ItemQuery:
        meta_params = self.meta_params.copy()
        meta_params["dataset_ids"] = str(self.datasets[0].id)
        meta_params["workflow_id"] = str(self.id)
        return ItemQuery(self.client, meta_params=meta_params)

    @property
    def stages(self) -> StageQuery:
        meta_params = self.meta_params.copy()
        meta_params["workflow_id"] = self._element.id
        if self.datasets is not None:
            meta_params["dataset_id"] = self.datasets[0].id
            meta_params["dataset_name"] = self.datasets[0].name
        return StageQuery(self.client, meta_params=meta_params)

    def _get_dataset_stage(self) -> Stage:
        # stages are not in right order - finding the dataset stage
        for stage in self.stages:
            if stage.type == "dataset":
                return stage

        raise MissingDataset("Workflow has no dataset stage")

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

    def push_from_dataset_stage(
        self, wait: bool = True, wait_max_attempts: int = 5, wait_time: float = 0.5
    ) -> Workflow:
        assert self._element.dataset is not None
        stages = self.stages
        assert len(stages) > 1

        ds_stage = self._get_dataset_stage()
        assert ds_stage._element.type == WFTypeCore.DATASET
        next_stage = ds_stage._element.edges[0].target_stage_id
        assert next_stage is not None
        ds_stage.move_attached_files_to_stage(
            next_stage, wait, wait_max_attempts, wait_time
        )

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
        wait: bool = True,
        wait_max_attempts: int = 5,
        wait_time: float = 0.5,
    ) -> Workflow:
        assert self._element.dataset is not None
        upload_data(
            self.datasets[0].name,
            files,  # type: ignore
            files_to_exclude,
            fps,
            path,
            frames,
            extract_views,
            preserve_folders,
            verbose,
        )
        if auto_push:
            self.push_from_dataset_stage(
                wait=wait, wait_max_attempts=wait_max_attempts, wait_time=wait_time
            )
        return self

    def __str__(self) -> str:
        return f"Workflow\n\
- Workflow Name: {self._element.name}\n\
- Workflow ID: {self._element.id}\n\
- Connected Dataset ID: {self.datasets[0].id}\n\
- Conneted Dataset Name: {self.datasets[0].name}"
