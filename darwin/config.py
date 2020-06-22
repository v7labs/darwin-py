import io
from pathlib import Path
from typing import Any, List, Optional, Union

import yaml

from darwin.exceptions import InvalidTeam


class Config(object):
    """Handles YAML configuration files"""

    def __init__(self, path: Union[Path, str, None]):
        """
            If path is None the config will be in memory only
        """
        if isinstance(path, str):
            path = Path(path)
        self._path = path
        self._data = self._parse()

    def _parse(self):
        """Parses the YAML configuration file"""
        if not self._path:
            return {}
        try:
            with open(self._path, "r") as stream:
                return yaml.safe_load(stream)
        except FileNotFoundError:
            return {}

    def get(self, key: Union[str, List[str]], default: Optional[any] = None) -> Any:
        """Gets value defined by key

        Args:
        - key: the key where the value to be fetched is stored.
        It can be formatted as a simple string, or as a path/like/string to fetch nested values.
        """

        acc = self._data.copy()

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

    def put(self, key: Union[str, List[str]], value: any, save: bool = True):
        """Sets value for specified key

        Args:
        - key: the key where the value is going to be stored.
        It can be formatted as a simple string, or as a path/like/string to fetch nested values.
        - value: the value to be set"""
        if isinstance(key, str):
            key = key.split("/")

        pointer = self._data

        for k in key[:-1]:
            pointer = pointer.setdefault(k, {})
        pointer[key[-1]] = str(value)

        if save:
            self._save()

    def _save(self):
        """Persist the configuration to the file system"""
        if not self._path:
            return
        with io.open(self._path, "w", encoding="utf8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def set_team(self, team: str, api_key: str, datasets_dir: str):
        self.put(f"teams/{team}/api_key", api_key)
        self.put(f"teams/{team}/datasets_dir", datasets_dir)

    def set_default_team(self, team: str):
        if self.get(f"teams/{team}") is None:
            raise InvalidTeam()
        self.put("global/default_team", team)

    def set_global(self, api_endpoint: str, base_url: str, default_team: Optional[str] = None):
        self.put("global/api_endpoint", api_endpoint)
        self.put("global/base_url", base_url)
        if default_team:
            self.put("global/default_team", default_team)

    def get_team(self, team: Optional[str] = None, raise_on_invalid_team: bool = True):
        if not team:
            return self.get_default_team(raise_on_invalid_team=raise_on_invalid_team)

        api_key = self.get(f"teams/{team}/api_key")
        if api_key is None:
            if raise_on_invalid_team:
                raise InvalidTeam()
            else:
                return None
        default = self.get("global/default_team") == team or len(list(self.get("teams").keys())) == 1

        datasets_dir = self.get(f"teams/{team}/datasets_dir")
        return {"slug": team, "api_key": api_key, "default": default, "datasets_dir": datasets_dir}

    def get_default_team(self, raise_on_invalid_team: bool = True):
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

    def get_all_teams(self):
        teams = list(self.get("teams").keys())
        return [self.get_team(slug) for slug in teams]
