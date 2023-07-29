from typing import List, Optional

from darwin.future.core.client import CoreClient
from darwin.future.data_objects.team import TeamMemberModel, get_team_members
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.meta.objects.base import MetaBase


class TeamMemberMeta(MetaBase[TeamMemberModel]):
    @property
    def role(self) -> TeamMemberRole:
        if self._item is None:
            raise ValueError("TeamMemberMeta has no item")
        return self._item.role
