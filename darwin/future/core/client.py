from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

import requests
import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from requests.adapters import HTTPAdapter, Retry

from darwin.config import Config as OldConfig
from darwin.future.core.types.common import JSONType, QueryString
from darwin.future.exceptions import (
    BadRequest,
    NotFound,
    Unauthorized,
    UnprocessibleEntity,
)


class TeamsConfig(BaseModel):
    api_key: str
    datasets_dir: Path


class DarwinConfig(BaseModel):
    """Configuration object for the client

    Attributes
    ----------
    api_key: Optional[str], api key to authenticate
    base_url: pydantic.HttpUrl, base url of the API
    default_team: Optional[Team], default team to make requests to
    """

    api_key: Optional[str] = None
    datasets_dir: Optional[Path] = None
    api_endpoint: str
    base_url: str
    default_team: str
    teams: Dict[str, TeamsConfig]

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        v = v.strip()
        if not v.endswith("/"):
            v += "/"
        check = urlparse(v)
        assert check.scheme in {
            "http",
            "https",
        }, "base_url must start with http or https"
        assert check.netloc, "base_url must contain a domain"
        return v

    @classmethod
    def _remove_global(cls, values: dict) -> dict:
        if "global" not in values:
            return values
        global_conf = values["global"]
        del values["global"]
        values.update(global_conf)
        return values

    @model_validator(mode="before")
    @classmethod
    def validate_defaults(cls, values: Any) -> Any:
        values = cls._remove_global(values)
        if "api_key" in values:
            return values
        assert values["default_team"] in values["teams"]
        team = values["default_team"]
        values["api_key"] = values["teams"][team]["api_key"]
        values["datasets_dir"] = values["teams"][team]["datasets_dir"]
        return values

    @staticmethod
    def _default_config_path() -> Path:
        return DarwinConfig._default_home_path() / "config.yaml"

    @staticmethod
    def _default_datasets_path() -> Path:
        return DarwinConfig._default_home_path() / "datasets"

    @staticmethod
    def _default_home_path() -> Path:
        return Path.home() / ".darwin"

    @staticmethod
    def local() -> DarwinConfig:
        return DarwinConfig.from_file(DarwinConfig._default_config_path())

    @staticmethod
    def _default_base_url() -> str:
        return "https://darwin.v7labs.com/"

    @staticmethod
    def _default_api_endpoint() -> str:
        return DarwinConfig._default_base_url() + "api/"

    @staticmethod
    def from_file(path: Path) -> DarwinConfig:
        if path.suffix.lower() == ".yaml":
            data = DarwinConfig._parse_yaml(path)
            return DarwinConfig.model_validate(data)
        else:
            return DarwinConfig.parse_file(path)

    @staticmethod
    def _parse_yaml(path: Path) -> dict:
        with open(path, encoding="utf-8") as infile:
            data = yaml.safe_load(infile)
        return data

    @staticmethod
    def from_api_key_with_defaults(api_key: str) -> DarwinConfig:
        return DarwinConfig(
            api_key=api_key,
            api_endpoint=DarwinConfig._default_api_endpoint(),
            base_url=DarwinConfig._default_base_url(),
            default_team="default",
            teams={},
            datasets_dir=DarwinConfig._default_config_path(),
        )

    @staticmethod
    def from_old(old_config: OldConfig, team_slug: str) -> DarwinConfig:
        teams = old_config.get("teams")
        if not teams:
            raise ValueError("No teams found in the old config")

        default_team = old_config.get("global/default_team")
        if not default_team:
            default_team = list(teams.keys())[0]

        return DarwinConfig(
            api_key=teams[team_slug]["api_key"],
            api_endpoint=old_config.get("global/api_endpoint"),
            base_url=old_config.get("global/base_url"),
            default_team=default_team,
            teams=teams,
            datasets_dir=teams[team_slug]["datasets_dir"],
        )

    model_config = ConfigDict(validate_assignment=True)


class Result(BaseModel):
    """Default model for a result, to be extended by other models specific to the API"""

    ...


class ClientCore:
    """Client Object to manage and make requests to the Darwin API
    Attributes
    ----------
    url: str, url of the endpoint
    api_key: str, api key to authenticate
    team: Team, team to make requests to
    """

    def __init__(
        self,
        config: DarwinConfig,
        retries: Optional[Retry] = None,
    ) -> None:
        self.config = config
        self.session = requests.Session()
        if not retries:
            retries = Retry(
                total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504]
            )
        self._setup_session(retries)
        self._mappings = {
            "get": self.session.get,
            "put": self.session.put,
            "post": self.session.post,
            "delete": self.session.delete,
            "patch": self.session.patch,
        }

    def _setup_session(self, retries: Retry) -> None:
        self.session.headers.update(self.headers)
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    @property
    def headers(self) -> Dict[str, str]:
        http_headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.config.api_key:
            http_headers["Authorization"] = f"ApiKey {self.config.api_key}"
        return http_headers

    def _generic_call(
        self, method: Callable, endpoint: str, payload: Optional[dict] = None
    ) -> JSONType:
        endpoint = self._sanitize_endpoint(endpoint)
        url = self.config.api_endpoint + endpoint
        if payload is not None:
            response = method(url, json=payload)
        else:
            response = method(url)

        raise_for_darwin_exception(response)
        response.raise_for_status()

        return response.json()

    def _contain_qs_and_endpoint(
        self, endpoint: str, query_string: Optional[QueryString] = None
    ) -> str:
        if not query_string:
            return endpoint

        assert "?" not in endpoint
        return endpoint + str(query_string)

    def get(
        self, endpoint: str, query_string: Optional[QueryString] = None
    ) -> JSONType:
        return self._generic_call(
            self.session.get, self._contain_qs_and_endpoint(endpoint, query_string)
        )

    def put(self, endpoint: str, data: dict) -> JSONType:
        return self._generic_call(self.session.put, endpoint, data)

    def post(self, endpoint: str, data: dict) -> JSONType:
        return self._generic_call(self.session.post, endpoint, data)

    def delete(
        self,
        endpoint: str,
        query_string: Optional[QueryString] = None,
        data: Optional[dict] = None,
    ) -> JSONType:
        return self._generic_call(
            self.session.delete,
            self._contain_qs_and_endpoint(endpoint, query_string),
            data,
        )

    def patch(self, endpoint: str, data: dict) -> JSONType:
        return self._generic_call(self.session.patch, endpoint, data)

    def _sanitize_endpoint(self, endpoint: str) -> str:
        return endpoint.strip().strip("/")


def raise_for_darwin_exception(response: requests.Response) -> None:
    """Raises an exception if the response.status_code matches a known darwin error

    Parameters
    ----------
    response: requests.Response, response to check
    """
    if response.status_code == 200:
        return
    if response.status_code == 400:
        raise BadRequest(response, response.text)
    if response.status_code == 401:
        raise Unauthorized(response, response.text)
    if response.status_code == 404:
        raise NotFound(response, response.text)
    if response.status_code == 422:
        raise UnprocessibleEntity(response, response.text)
