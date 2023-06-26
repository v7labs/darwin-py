from typing import List, Optional, Tuple, Union

from darwin.future.helpers.assertion import assert_is
from darwin.future.meta.client import MetaClient
from darwin.future.meta.queries.team_member import TeamMemberQuery


class DatasetMeta:
    client: MetaClient

    def __init__(self, client: MetaClient) -> None:
        # TODO: Initialise from chaining within MetaClient
        self.client = client

    @property
    def members(self) -> TeamMemberQuery:
        return TeamMemberQuery(self.client)