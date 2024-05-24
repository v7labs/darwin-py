from darwin.future.data_objects.team import TeamMemberCore
from darwin.future.data_objects.team_member_role import TeamMemberRole
from darwin.future.meta.objects.base import MetaBase


class TeamMember(MetaBase[TeamMemberCore]):
    """
    Team Member Meta object. Facilitates the creation of Query objects, lazy loading of
    sub fields

    Args:
        MetaBase (TeamMember): Generic MetaBase object expanded by TeamMemberCore object
            return type

    Returns:
        _type_: TeamMember

    Attributes:
        first_name (str): The first name of the team member.
        last_name (str): The last name of the team member.
        email (str): The email of the team member.
        user_id (int): The user id of the team member.
        role (TeamMemberRole): The role of the team member.

    Methods:
        None

    Example Usage:
        # Get the role of the team member
        team_member = client.team.members
            .where(first_name='John', last_name='Doe')
            .collect_one()

        role = team_member.role
    """

    @property
    def role(self) -> TeamMemberRole:
        return self._element.role

    @property
    def first_name(self) -> str:
        return self._element.first_name

    @property
    def last_name(self) -> str:
        return self._element.last_name

    @property
    def email(self) -> str:
        return self._element.email

    @property
    def user_id(self) -> int:
        return self._element.user_id

    def __str__(self) -> str:
        return f"Team Member\n\
- Name: {self.first_name} {self.last_name}\n\
- Role: {self.role.value}\n\
- Email: {self.email}\n\
- User ID: {self.user_id}"
