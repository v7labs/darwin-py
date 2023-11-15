from __future__ import annotations

from typing import List
from uuid import UUID

from darwin.future.core.items import move_items_to_stage
from darwin.future.core.types.query import QueryFilter
from darwin.future.data_objects.workflow import WFEdgeCore, WFStageCore
from darwin.future.meta.objects.base import MetaBase
from darwin.future.meta.queries.item import ItemQuery
from darwin.future.meta.queries.item_id import ItemIDQuery


class Stage(MetaBase[WFStageCore]):
    """
    Stage Meta object. Facilitates the creation of Query objects, lazy loading of
    sub fields

    Args:
        MetaBase (Stage): Generic MetaBase object expanded by WFStageCore object
            return type

    Returns:
        _type_: Stage

    Attributes:
        name (str): The name of the stage.
        slug (str): The slug of the stage.
        id (UUID): The id of the stage.
        item_ids (List[UUID]): A list of item ids attached to the stage.
        edges (List[WFEdgeCore]): A list of edges attached to the stage.

    Methods:
        move_attached_files_to_stage(new_stage_id: UUID) -> Stage:
            Moves all attached files to a new stage.

    Example Usage:
        # Get the item ids attached to the stage
        stage = client.team.workflows.where(name='test').stages[0]
        item_ids = stage.item_ids

        # Move all attached files to a new stage
        new_stage = stage.edges[1]
        stage.move_attached_files_to_stage(new_stage_id=new_stage.id)
    """

    @property
    def items(self) -> ItemQuery:
        """Item ids attached to the stage

        Returns:
            List[Item]: List of item ids
        """
        assert self._element.id is not None
        return ItemQuery(
            self.client,
            meta_params=self.meta_params,
            filters=[
                QueryFilter(name="workflow_stage_ids", param=str(self._element.id))
            ],
        )

    @property
    def item_ids(self) -> ItemIDQuery:
        """Item ids attached to the stage

        Returns:
            List[UUID]: List of item ids
        """
        assert self._element.id is not None
        return ItemIDQuery(
            self.client,
            meta_params=self.meta_params,
            filters=[
                QueryFilter(name="workflow_stage_ids", param=str(self._element.id))
            ],
        )

    def move_attached_files_to_stage(self, new_stage_id: UUID) -> Stage:
        assert self.meta_params["team_slug"] is not None and isinstance(
            self.meta_params["team_slug"], str
        )
        assert self.meta_params["workflow_id"] is not None and isinstance(
            self.meta_params["workflow_id"], UUID
        )
        assert self.meta_params["dataset_id"] is not None and isinstance(
            self.meta_params["dataset_id"], int
        )
        team_slug, workflow_id, dataset_id = (
            self.meta_params["team_slug"],
            self.meta_params["workflow_id"],
            self.meta_params["dataset_id"],
        )
        ids = [str(x.id) for x in self.item_ids.collect_all()]
        move_items_to_stage(
            self.client,
            team_slug,
            workflow_id,
            dataset_id,
            new_stage_id,
            {"item_ids": ids},
        )
        return self

    @property
    def id(self) -> UUID:
        """Stage ID."""
        return self._element.id

    @property
    def name(self) -> str:
        """Stage name."""
        return self._element.name

    @property
    def type(self) -> str:
        """Stage type."""
        return self._element.type.value

    @property
    def edges(self) -> List[WFEdgeCore]:
        """Edge ID, source stage ID, target stage ID."""
        return list(self._element.edges)

    def __str__(self) -> str:
        return f"Stage\n\
- Stage Name: {self._element.name}\n\
- Stage Type: {self._element.type.value}\n\
- Stage ID: {self._element.id}"
