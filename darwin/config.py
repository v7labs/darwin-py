import io
from pathlib import Path
from typing import Any, List, Optional, Union

import yaml


class Config(object):
    """Handles YAML configuration files"""

    def __init__(self, path: Union[Path, str], data: Optional[dict] = None):
        if isinstance(path, str):
            path = Path(path)
        self._path = path

        if data is None:
            self._data = self.parse()
        else:
            self._data = data
            self._save()

    def get(self, key: Union[str, List[str]], acc: dict = None) -> Any:
        """Gets value defined by key
        
        Args:
        - key: the key where the value to be fetched is stored.
        It can be formatted as a simple string, or as a path/like/string to fetch nested values.
        """

        if acc is None:
            acc = self._data.copy()

        if isinstance(key, str):
            key = key.split("/")
        key, *keys = key
        if len(keys) == 0:
            return acc.get(key)
        return self.get(keys, acc.get(key))

    def parse(self):
        """Parses the YAML configuration file"""

        with open(self._path, "r") as stream:
            return yaml.safe_load(stream)

    def write(self, key: Union[str, List[str]], value: Any, save: bool = True):
        """Sets value for specified key
        
        Args:
        - key: the key where the value is going to be stored.
        It can be formatted as a simple string, or as a path/like/string to fetch nested values.
        - value: the value to be set"""

        if isinstance(key, str):
            key = key.split("/")
        for k in key[:-1]:
            self._data = self._data.setdefault(k, {})
        self._data[key[-1]] = value
        if save:
            self._save()

    def _save(self):
        with io.open(self._path, "w", encoding="utf8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)
