import os
from pathlib import Path
from typing import Dict, Optional

import requests

from darwin.config import Config
from darwin.dataset import Dataset, LocalDataset
from darwin.exceptions import (
    InsufficientStorage,
    InvalidLogin,
    MissingConfig,
    NameTaken,
    NotFound,
    Unauthenticated,
    ValidationError,
)
from darwin.team import Team
from darwin.utils import is_project_dir, urljoin


class Client:
    def __init__(
        self, token: str, refresh_token: str, api_url: str, base_url: str, projects_dir: str
    ):
        self._token = token
        self._refresh_token = refresh_token
        self._url = api_url
        self._base_url = base_url
        self._team = None
        # TODO: read this from config
        self.project_dir = projects_dir

    @classmethod
    def default(cls):
        config_path = Path.home() / ".darwin" / "config.yaml"
        return Client.from_config(config_path)

    @classmethod
    def from_config(cls, config_path_str: str):
        config_path: Path = Path(config_path_str)
        if not config_path.exists():
            raise MissingConfig()
        config = Config(config_path)
        return cls(
            token=config.get("token"),
            refresh_token=config.get("refresh_token"),
            api_url=config.get("api_endpoint"),
            base_url=config.get("base_url"),
            projects_dir=config.get("projects_dir"),
        )

    @classmethod
    def login(cls, email: str, password: str, projects_dir_str: Optional[str] = None):
        if projects_dir_str is None:
            projects_dir = Path.home() / ".darwin" / "projects"
        else:
            projects_dir = Path(projects_dir_str)
        api_url = Client.default_api_url()
        response = requests.post(
            urljoin(api_url, "/users/authenticate"),
            headers={"Content-Type": "application/json"},
            json={"email": email, "password": password},
        )
        if response.status_code != 200:
            raise InvalidLogin()
        data = response.json()
        return cls(
            token=data["token"],
            refresh_token=data["refresh_token"],
            api_url=api_url,
            base_url=Client.default_base_url(),
            projects_dir=str(projects_dir),
        )

    @staticmethod
    def default_api_url():
        return os.getenv("DARWIN_API_URL", "https://darwin.v7labs.com/api/")

    @staticmethod
    def default_base_url():
        if os.getenv("DARWIN_BASE_URL"):
            return os.getenv("DARWIN_BASE_URL")
        return Client.default_api_url().replace("/api", "")

    def _refresh_access_token(self):
        response = requests.get(
            urljoin(self._url, "/refresh"), headers=self._get_headers(refresh=True)
        )
        if response.status_code != 200:
            raise Unauthenticated()

        data = response.json()
        self._token = data["token"]

    def _ensure_authenticated(self):
        if self._token is None:
            if self._refresh_token is None:
                raise Unauthenticated()
            else:
                self._refresh_access_token()

    def _get_headers(self, refresh=False):
        if refresh:
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._refresh_token}",
            }
        else:
            return {"Content-Type": "application/json", "Authorization": f"Bearer {self._token}"}

    def get(self, endpoint: str, retry: bool = True, raw: bool = False):
        self._ensure_authenticated()
        response = requests.get(urljoin(self._url, endpoint), headers=self._get_headers())

        if response.status_code == 401:
            self._refresh_access_token()
            return self.get(endpoint, retry=False)

        if response.status_code != 200:
            print("TODO, fix me get", response.json(), response.status_code)

        if raw:
            return response
        return response.json()

    def put(self, endpoint: str, payload: Dict, retry: bool = True):
        self._ensure_authenticated()
        response = requests.put(
            urljoin(self._url, endpoint), json=payload, headers=self._get_headers()
        )

        if response.status_code == 401:
            self._refresh_access_token()
            return self.put(endpoint, payload, retry=False)
        if response.status_code == 429:
            error_code = response.json()["errors"]["code"]
            if error_code == "INSUFFICIENT_REMAINING_STORAGE":
                raise InsufficientStorage()

        if response.status_code != 200:
            print("TODO, fix me put", response, response.status_code)
        return response.json()

    def post(
        self,
        endpoint: str,
        payload: Dict = {},
        retry: bool = True,
        refresh=False,
        error_handlers=[],
    ):
        self._ensure_authenticated()
        response = requests.post(
            urljoin(self._url, endpoint), json=payload, headers=self._get_headers(refresh=refresh)
        )

        if response.status_code == 401:
            self._refresh_access_token()
            return self.post(endpoint, payload=payload, retry=False)

        if response.status_code != 200:
            for error_handler in error_handlers:
                error_handler(response.status_code, response.json())
            print("TODO, fix me post", response, response.status_code)
        return response.json()

    def current_team(self):
        data = self.get("/users/token_info")["selected_team"]
        return Team(id=data["id"], name=data["name"], slug=data["slug"], selected=True)

    def list_teams(self):
        data = self.get("/users/token_info")
        teams = []
        for row in data["teams"]:
            teams.append(
                Team(
                    id=row["id"],
                    name=row["name"],
                    slug=row["slug"],
                    selected=data["selected_team"]["id"] == row["id"],
                )
            )
        return teams

    def set_team(self, slug: str):
        teams = self.list_teams()

        matching_team = [team for team in teams if team.slug == slug]
        if not matching_team:
            raise NotFound

        data = self.post("/users/select_team", {"team_id": matching_team[0].id}, refresh=True)
        self._token = data["token"]
        self._refresh_token = data["refresh_token"]

    def list_remote_datasets(self):
        projects = self.get("/projects/")
        for project in projects:
            yield Dataset(
                project["name"],
                slug=project["slug"],
                dataset_id=project["dataset_id"],
                project_id=project["id"],
                image_count=project["num_images"],
                progress=project["progress"],
                client=self,
            )

    def list_local_datasets(self):
        for project_path in Path(self.project_dir).glob("*"):
            if project_path.is_dir() and is_project_dir(project_path):
                yield LocalDataset(project_path=project_path, client=self)

    def get_remote_dataset(
        self,
        *,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        dataset_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ):
        # TODO: swap project_id for dataset_id when the backend has gotten ride of project_id
        if project_id:
            project = self.get(f"/projects/{project_id}")
            return Dataset(
                project["name"],
                slug=project["slug"],
                dataset_id=project["dataset_id"],
                project_id=project["id"],
                image_count=project["num_images"],
                progress=project["progress"],
                client=self,
            )
        if slug:
            # TODO: when the backend have support for slug fetching update this.
            matching_datasets = [
                dataset for dataset in self.list_remote_datasets() if dataset.slug == slug
            ]
            if not matching_datasets:
                raise NotFound
            return matching_datasets[0]
        if name:
            print("Sorry, no support for name yet")
            raise NotImplementedError
        if dataset_id:
            print("Sorry, no support for dataset_id yet")
            raise NotImplementedError

    def get_local_dataset(self, *, slug: str):
        if slug:
            matching_datasets = [
                dataset for dataset in self.list_local_datasets() if dataset.slug == slug
            ]
            if not matching_datasets:
                raise NotFound
            return matching_datasets[0]

    def create_dataset(self, name: str):
        team = self.current_team()

        project = self.post(
            "/projects",
            {"name": name, "team_id": team.id},
            error_handlers=[name_taken, validation_error],
        )
        return Dataset(
            project["name"],
            slug=project["slug"],
            dataset_id=project["dataset_id"],
            project_id=project["id"],
            image_count=project["num_images"],
            progress=project["progress"],
            client=self,
        )


def name_taken(code, body):
    if code == 422 and body["errors"]["name"][0] == "has already been taken":
        raise NameTaken


def validation_error(code, body):
    if code == 422:
        raise ValidationError
