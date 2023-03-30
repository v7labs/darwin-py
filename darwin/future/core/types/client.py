from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, HttpUrl

from darwin.future.core.types.query import Query
from darwin.future.data_objects.darwin_meta import Team


class Config(BaseModel):
    """Configuration object for the client

    Attributes
    ----------
    base_url: pydantic.HttpUrl, base url of the API
    default_team: Optional[Team], default team to make requests to
    """

    base_url: HttpUrl
    default_team: Optional[Team]

    def from_env(cls) -> Config:
        pass

    def from_file(cls, path: Path) -> Config:
        pass


class Result(BaseModel):
    """Default model for a result, to be extended by other models specific to the API"""

    pass


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


class Cursor(ABC):
    """Abstract class for a cursor

    Attributes
    ----------
    url: str, url of the endpoint
    client: Client, client used to make requests
    """

    def __init__(self, url: str, client: Client):
        self.url = url
        self.client = client
        self.current_page: Optional[Page] = None

    @abstractmethod
    def execute(self, query: Query) -> Page:
        pass

    @abstractmethod
    def __iter__(self) -> Page:
        pass

    @abstractmethod
    def __next__(self) -> Page:
        pass


class Client:
    """Client Object to manage and make requests to the Darwin API
    Attributes
    ----------
    url: str, url of the endpoint
    api_key: str, api key to authenticate
    team: Team, team to make requests to
    """

    def __init__(self, config: Config) -> None:
        self.config = config

    def cursor(self) -> Cursor:
        pass

    def get(self, url: str) -> dict:
        pass

    def put(self, url: str, data: dict) -> dict:
        pass

    def post(self, url: str, data: dict) -> dict:
        pass

    def delete(self, url: str) -> dict:
        pass

    def patch(self, url: str, data: dict) -> dict:
        pass
