from typing import List, Optional

from darwin.future.core.client import Client
from darwin.future.data_objects.team import TeamMember, get_team_members
from darwin.future.meta.objects.base import MetaBase


class TeamMembersMeta(MetaBase[TeamMember]):
    client: Client

    def __init__(self, client: Client, members: Optional[List[TeamMember]]=None) -> None:
        # TODO: Initialise from chaining within MetaClient
        self.client = client
        super().__init__(members)

    def __next__(self) -> TeamMember:
        if self._items is None:
            items, exceptions = get_team_members(self.client)
            self._items = items
        return super().__next__()
    