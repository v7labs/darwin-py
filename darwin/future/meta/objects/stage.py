from typing import List, Optional
from uuid import UUID

from darwin.future.core.client import Client
from darwin.future.core.items.get import get_item_ids_stage
from darwin.future.data_objects.workflow import WFStage
from darwin.future.meta.objects.base import MetaBase


class StageMeta(MetaBase[WFStage]):
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
        assert self._item is not None
        assert self._item.id is not None
        return get_item_ids_stage(
            self.client, str(self.meta_params["team_slug"]), str(self.meta_params["dataset_id"]), self.id
        )

    @property
    def id(self) -> UUID:
        assert self._item is not None
        return self._item.id
