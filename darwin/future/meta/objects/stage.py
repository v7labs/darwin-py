from __future__ import annotations

from typing import List
from uuid import UUID

from darwin.future.core.items import get_item_ids_stage, move_items_to_stage
from darwin.future.data_objects.workflow import WFStageCore
from darwin.future.meta.objects.base import MetaBase


class Stage(MetaBase[WFStageCore]):
    """_summary_

    Args:
        MetaBase (_type_): _description_
    """

    @property
    def item_ids(self) -> List[UUID]:
        """_summary_

        Returns:
            _type_: _description_
        """
        assert self._element.id is not None
        return get_item_ids_stage(
            self.client, str(self.meta_params["team_slug"]), str(self.meta_params["dataset_id"]), self.id
        )

    def move_attached_files_to_stage(self, new_stage_id: UUID) -> Stage:
        assert self.meta_params["team_slug"] is not None and type(self.meta_params["team_slug"]) == str
        assert self.meta_params["workflow_id"] is not None and type(self.meta_params["workflow_id"]) == UUID
        assert self.meta_params["dataset_id"] is not None and type(self.meta_params["dataset_id"]) == int
        slug, w_id, d_id = (
            self.meta_params["team_slug"],
            self.meta_params["workflow_id"],
            self.meta_params["dataset_id"],
        )
        move_items_to_stage(self.client, slug, w_id, d_id, new_stage_id, self.item_ids)
        return self

    @property
    def id(self) -> UUID:
        return self._element.id
