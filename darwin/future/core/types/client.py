from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel

from darwin.future.core.types.query import Query
from darwin.future.data_objects.darwin_meta import Team


class Result(BaseModel):
    """Default model for a result, to be extended by other models sepcific to the API"""

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

    def __init__(self, url: str, client: "Client"):
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
    def __init__(self, url: str, api_key: str, team: Team) -> None:
        self.url = url
        self.api_key = api_key
        self.team = team

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
