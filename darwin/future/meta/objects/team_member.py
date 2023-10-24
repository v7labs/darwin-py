from darwin.future.data_objects.team import TeamMemberCore
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.meta.objects.base import MetaBase


class TeamMember(MetaBase[TeamMemberCore]):
    @property
    def role(self) -> TeamMemberRole:
        return self._element.role

    def __str__(self) -> str:
        return f"Team Member\n\
- Name: {self._element.first_name} {self._element.last_name}\n\
- Role: {self._element.role.value}\n\
- Email: {self._element.email}\n\
- User ID: {self._element.user_id}"
