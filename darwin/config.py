import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from darwin.datatypes import PathLike, Team
from darwin.exceptions import InvalidCompressionLevel, InvalidTeam


class Config(object):
    """Handles YAML configuration files"""

    def __init__(self, path: Optional[PathLike] = None):
        """
        If path is None the config will be in memory only
        """
        if isinstance(path, str):
            path = Path(path)

        self._path: Optional[Path] = path
        self._data: Dict[str, Any] = self._parse()

    def _parse(self) -> Dict[str, Any]:
        """Parses the YAML configuration file"""
        if not self._path:
            return {}
        try:
            with open(self._path, "r") as stream:
                return yaml.safe_load(stream)
        except FileNotFoundError:
            return {}

    def get(self, key: Union[str, List[str]], default: Optional[Any] = None) -> Any:
        """
        Gets the value defined by key.

        Parameters
        ----------
        key: Union[str, List[str]]
            The key where the value to be fetched is stored.
            It can be formatted as a simple string, or as a path/like/string to fetch nested values.
        default: Optional[Any]
            A default value in case the given key returns ``None``. Defaults to ``None``.

        Returns
        -------
        Any
            The value stored by the key.
        """

        acc: Any = self._data.copy()

        while True:
            if isinstance(key, str):
                key = key.split("/")
            key, *keys = key
            acc = acc.get(key)
            if acc is None:
                return default
            if len(keys) == 0:
                return acc
            else:
                key = keys

    def put(self, key: Union[str, List[str]], value: Any, save: bool = True) -> None:
        """
        Sets the value for the specified key.

        Parameters
        ----------
        key: Union[str, List[str]]
            The key where the value is going to be stored.
            It can be formatted as a simple string, or as a path/like/string to fetch nested values.
        value: Any
            The value to be stored.
        save: bool
            If ``True``, persists the value in the FileSystem. Defaults to ``True``.
        """
        if isinstance(key, str):
            key = key.split("/")

        pointer = self._data

        for k in key[:-1]:
            pointer = pointer.setdefault(k, {})
        pointer[key[-1]] = str(value)

        if save:
            self._save()

    def _save(self) -> None:
        """Persist the configuration to the file system"""
        if not self._path:
            return
        with io.open(self._path, "w", encoding="utf8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def set_team(self, team: str, api_key: str, datasets_dir: str) -> None:
        """
        Stores the API key and Dataset directory for the given team.

        Parameters
        ----------
        team: str
            The name of the team.
        api_key: str
            The API key the user has to do actions in the given team.
        datasets_dir: str
            The directory to stores datasets from the given team.
        """
        self.put(f"teams/{team}/api_key", api_key)
        self.put(f"teams/{team}/datasets_dir", datasets_dir)

    def set_default_team(self, team: str) -> None:
        """
        Sets the given team as the default one.

        Parameters
        ----------
        team: str
            The team's slug.

        Raises
        ------
        InvalidTeam
            If the given team is not in the configuration file. Authenticate with this team first
            to avoid this issue.
        """
        if self.get(f"teams/{team}") is None:
            raise InvalidTeam()
        self.put("global/default_team", team)

    def set_compression_level(self, level: int) -> None:
        """
        Sets the given compression level globally.

        Parameters
        ----------
        level: int
            The compression level.

        Raises
        ------
        InvalidCompressionLevel
            Compression level is out of supported range. Use number from 0 to 9 to avoid this issue.
        """
        if level < 0 or level > 9:
            raise InvalidCompressionLevel(level)
        self.put("global/payload_compression_level", level)

    def set_global(self, api_endpoint: str, base_url: str, default_team: Optional[str] = None) -> None:
        """
        Stores the url to access teams. If a default team is given, it also stores that team as the
        globaly default one.

        Parameters
        ----------
        api_endpoint: str
            The '/api' endpoint from V7's API.
        base_url: str
            The base URL for V7 together with protocol.
        default_team: Optional[str]
            The default team's slug. Defaults to ``None``.
        """
        self.put("global/api_endpoint", api_endpoint)
        self.put("global/base_url", base_url)
        if default_team:
            self.put("global/default_team", default_team)

    def get_team(self, team: Optional[str] = None, raise_on_invalid_team: bool = True) -> Optional[Team]:
        """
        Returns the Team object from the team with the given slug if an authentication with an API
        key was performed earlier.

        Parameters
        ----------
        team: Optional[str]
            The Team's slug. If none is given, searches for the default team instead. Defaults to
            ``None``.
        raise_on_invalid_team: bool
            If ``True``, raises if no team is found, if False returns ``None`` instead. Defaults to ``True``.

        Returns
        -------
        Optional[Team]:
            The team or ``None`` if no API key for the team was found and `raise_on_invalid_team` is
            ``False``.

        Raises
        ------
        InvalidTeam
            If the user has not been authenticated with an API key for they given team.
        """
        if not team:
            return self.get_default_team(raise_on_invalid_team=raise_on_invalid_team)

        api_key = self.get(f"teams/{team}/api_key")
        if api_key is None:
            if raise_on_invalid_team:
                raise InvalidTeam()
            else:
                return None
        default: bool = self.get("global/default_team") == team or len(list(self.get("teams").keys())) == 1

        datasets_dir = self.get(f"teams/{team}/datasets_dir")
        return Team(slug=team, api_key=api_key, default=default, datasets_dir=datasets_dir)

    def get_default_team(self, raise_on_invalid_team: bool = True) -> Optional[Team]:
        """
        Returns the default Team if one is defined.

        Parameters
        ----------
        raise_on_invalid_team: bool
            If ``True``, raises if no default team is found, if False returns ``None`` instead. Defaults
            to ``True``.

        Returns
        -------
        Optional[Team]:
            The team or ``None`` if no default team is set and `raise_on_invalid_team` is ``False``.

        Raises
        ------
        InvalidTeam
            If the user has not set a default team.
        """
        default_team = self.get("global/default_team")
        if default_team:
            return self.get_team(default_team)
        teams = list((self.get("teams") or {}).keys())
        if len(teams) != 1:
            if raise_on_invalid_team:
                raise InvalidTeam()
            else:
                return None
        return self.get_team(teams[0])

    def get_all_teams(self) -> List[Team]:
        """
        Returns a list of all teams saved in the configuration file.

        Returns
        -------
        List[Team]
            The list of teams saved.
        """
        teams = list(self.get("teams").keys())
        teams_data: List[Team] = []
        for slug in teams:
            the_team_data = self.get_team(slug)
            if the_team_data:
                teams_data.append(the_team_data)

        return teams_data
