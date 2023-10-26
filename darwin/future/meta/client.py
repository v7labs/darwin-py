from __future__ import annotations

from pathlib import Path
from typing import Optional

from requests.adapters import Retry

from darwin.future.core.client import ClientCore, DarwinConfig
from darwin.future.meta.objects.team import Team


class Client(ClientCore):
    """
    The Darwin Client object. Provides access to Darwin's API.

    Args:
        ClientCore (Client): Generic ClientCore object expanded by DarwinConfig object
            return type

    Returns:
        _type_: Client

    Attributes:
        _team (Optional[Team]): The team associated with the client.

    Methods:
        local(cls) -> Client: Creates a new client object with a local DarwinConfig.
        from_api_key(cls, api_key: str, datasets_dir: Optional[Path] = None) -> Client:
            Creates a new client object with a DarwinConfig from an API key.

    Example Usage:
        # Create a new client object with a local DarwinConfig
        client = Client.local()

        # Create a new client object with a DarwinConfig from an API key
        client = Client.from_api_key(api_key="my_api_key", datasets_dir="path/to/datasets/dir")

        # Access the team via chaining
        team = client.team # returns a Team object which can be chained further
    """

    def __init__(self, config: DarwinConfig, retries: Optional[Retry] = None) -> None:
        self._team: Optional[Team] = None
        super().__init__(config, retries=retries)

    @classmethod
    def local(cls) -> Client:
        config = DarwinConfig.local()
        return cls(config)

    @classmethod
    def from_api_key(cls, api_key: str, datasets_dir: Optional[Path] = None) -> Client:
        config = DarwinConfig.from_api_key_with_defaults(api_key=api_key)
        client = ClientCore(config)  # create a temporary client to get the default team
        token_info = client.get("/users/token_info")
        assert isinstance(token_info, dict)
        default_team: str = token_info["selected_team"]["slug"]
        config.default_team = default_team
        if datasets_dir:
            config.datasets_dir = datasets_dir
        return cls(config)

    @property
    def team(self) -> Team:
        if self._team is None:
            self._team = Team(self)
        return self._team

    # @property
    # def workflows(self) -> WorkflowQuery:
    #     return WorkflowQuery(self, meta_params={"team_slug": self.team.slug})
