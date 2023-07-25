from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from requests.adapters import Retry

from darwin.future.core.client import Client, DarwinConfig
from darwin.future.meta.objects.team import TeamMeta
from darwin.future.meta.objects.workflow import WorkflowMeta
from darwin.future.meta.queries.workflow import WorkflowQuery


class MetaClient(Client):
    def __init__(self, config: DarwinConfig, retries: Optional[Retry] = None) -> None:
        self._team: Optional[TeamMeta] = None
        super().__init__(config, retries=retries)

    @classmethod
    def local(cls) -> MetaClient:
        config = DarwinConfig.local()
        return cls(config)

    @classmethod
    def from_api_key(cls, api_key: str, datasets_dir: Optional[Path] = None) -> MetaClient:
        config = DarwinConfig.from_api_key_with_defaults(api_key=api_key)
        client = Client(config)  # create a temporary client to get the default team
        token_info = client.get("/users/token_info")
        assert isinstance(token_info, dict)
        default_team: str = token_info["selected_team"]["slug"]
        config.default_team = default_team
        if datasets_dir:
            config.datasets_dir = datasets_dir
        return cls(config)

    @property
    def team(self) -> TeamMeta:
        if self._team is None:
            self._team = TeamMeta(self)
        return self._team

    # @property
    # def workflows(self) -> WorkflowQuery:
    #     return WorkflowQuery(self, meta_params={"team_slug": self.team.slug})
