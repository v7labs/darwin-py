from darwin.future.data_objects.team import TeamMemberCore
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.meta.objects.base import MetaBase


class TeamMember(MetaBase[TeamMemberCore]):
    @property
    def role(self) -> TeamMemberRole:
        return self._element.role
