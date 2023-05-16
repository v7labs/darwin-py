from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, overload
from urllib.parse import urlparse

import requests
import yaml
from pydantic import BaseModel, root_validator, validator
from requests.adapters import HTTPAdapter, Retry

from darwin.future.core.types.common import QueryString
from darwin.future.exceptions.client import NotFound, Unauthorized

JSONType = Dict[str, Any]  # type: ignore


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

    api_key: Optional[str]
    datasets_dir: Optional[Path]
    api_endpoint: str
    base_url: str
    default_team: str
    teams: Dict[str, TeamsConfig]

    @validator("base_url")
    def validate_base_url(cls, v: str) -> str:
        v = v.strip()
        if not v.endswith("/"):
            v += "/"
        check = urlparse(v)
        assert check.scheme in {"http", "https"}, "base_url must start with http or https"
        assert check.netloc, "base_url must contain a domain"
        return v

    @root_validator(pre=True)
    def remove_global(cls, values: dict) -> dict:
        if "global" not in values:
            return values
        global_conf = values["global"]
        del values["global"]
        values.update(global_conf)
        return values

    @root_validator()
    def validate_defaults(cls, values: dict) -> dict:
        if values["api_key"]:
            return values
        assert values["default_team"] in values["teams"]
        team = values["default_team"]
        values["api_key"] = values["teams"][team].api_key
        values["datasets_dir"] = values["teams"][team].datasets_dir
        return values

    @staticmethod
    def local() -> DarwinConfig:
        return DarwinConfig.from_file(Path.home() / ".darwin" / "config.yaml")

    @staticmethod
    def from_file(path: Path) -> DarwinConfig:
        if path.suffix.lower() == ".yaml":
            data = DarwinConfig._parse_yaml(path)
            return DarwinConfig.parse_obj(data)
        else:
            return DarwinConfig.parse_file(path)

    @staticmethod
    def _parse_yaml(path: Path) -> dict:
        with open(path, encoding="utf-8") as infile:
            data = yaml.safe_load(infile)
        return data

    class Config:
        validate_assignment = True


class Result(BaseModel):
    """Default model for a result, to be extended by other models specific to the API"""

    ...


class PageDetail(BaseModel):
    """Page details model for managing pagination

    Attributes
    ----------
    count: int, current position
    next: Optional[str], url for the next page
    previous: Optional[str], url for the previous page
    """

    count: int
    next: Optional[str]
    previous: Optional[str]


class Page(BaseModel):
    """Page of results

    Attributes
    ----------
    results: List[Result], list of results
    detail: PageDetail, details about the page
    """

    results: List[Result]
    detail: PageDetail


class Client:
    """Client Object to manage and make requests to the Darwin API
    Attributes
    ----------
    url: str, url of the endpoint
    api_key: str, api key to authenticate
    team: Team, team to make requests to
    """

    def __init__(self, config: DarwinConfig, retries: Optional[Retry] = None) -> None:
        self.config = config
        self.session = requests.Session()
        if not retries:
            retries = Retry(total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
        self._setup_session(retries)
        self._mappings = {
            "get": self.session.get,
            "put": self.session.put,
            "post": self.session.post,
            "delete": self.session.delete,
            "patch": self.session.patch,
        }

    @classmethod
    def local(cls) -> Client:
        config = DarwinConfig.local()
        return Client(config)

    def _setup_session(self, retries: Retry) -> None:
        self.session.headers.update(self.headers)
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    @property
    def headers(self) -> Dict[str, str]:
        http_headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            http_headers["Authorization"] = f"ApiKey {self.config.api_key}"
        return http_headers

    @overload
    def _generic_call(self, method: Callable[[str], requests.Response], endpoint: str) -> dict:
        ...

    @overload
    def _generic_call(self, method: Callable[[str, dict], requests.Response], endpoint: str, payload: dict) -> dict:
        ...

    def _generic_call(self, method: Callable, endpoint: str, payload: Optional[dict] = None) -> JSONType:
        endpoint = self._sanitize_endpoint(endpoint)
        url = self.config.api_endpoint + endpoint
        if payload is not None:
            response = method(url, payload)
        else:
            response = method(url)

        raise_for_darwin_exception(response)
        response.raise_for_status()

        return response.json()

    def get(self, endpoint: str) -> JSONType:
        return self._generic_call(self.session.get, endpoint)

    def put(self, endpoint: str, data: dict) -> JSONType:
        return self._generic_call(self.session.put, endpoint, data)

    def post(self, endpoint: str, data: dict) -> JSONType:
        return self._generic_call(self.session.post, endpoint, data)

    def delete(self, endpoint: str, query_string: Optional[QueryString] = None) -> JSONType:
        return self._generic_call(self.session.delete, self._contain_qs_and_endpoint(endpoint, query_string))

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
    if response.status_code == 401:
        raise Unauthorized(response)
    if response.status_code == 404:
        raise NotFound(response)
