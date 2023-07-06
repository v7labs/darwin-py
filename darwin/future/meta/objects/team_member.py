from typing import List, Optional

from darwin.future.core.client import Client
from darwin.future.data_objects.team import TeamMember, get_team_members
from darwin.future.meta.objects.base import MetaBase


class TeamMemberMeta(MetaBase[TeamMember]):
    pass
