from typing import List, Optional

from darwin.future.core.client import Client
from darwin.future.data_objects.team import TeamMember, get_team, get_team_members
from darwin.future.meta.objects.base import MetaBase


class TeamMembersMeta(MetaBase[TeamMember]):
    client: Client

    def __init__(self, client: Client, members: Optional[List[TeamMember]]=None) -> None:
        # TODO: Initialise from chaining within MetaClient
        self.client = client
        self.members = members

    def __next__(self) -> TeamMember:
        if self.members is None:
            self.members = get_team_members(self.client)
        if self.n < len(self.members):
            result = self.members[self.n]
            self.n += 1
            return result
        else:
            raise StopIteration
    
    def __len__(self) -> int:
        if self.members is None:
            self.members = get_team_members(self.client)
        return len(self.members)
    
    def __getitem__(self, index: int) -> TeamMember:
        if self.members is None:
            self.members = get_team_members(self.client)
        return self.members[index]