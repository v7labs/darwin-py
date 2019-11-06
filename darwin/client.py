import os
from pathlib import Path
from typing import Dict, Optional, Iterator

import requests

from darwin.config import Config
from darwin.dataset import RemoteDataset
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
        self,
        token: str,
        api_url: str,
        base_url: str,
        projects_dir: Path,
        refresh_token: Optional[str] = None,  # TODO verify nothing breaks
    ):
        """Initializes a Client object. Clients are responsible for holding the logic and for
        interacting with the remote hosts.

        Parameters
        ----------
        token : str
            Access token used to auth a specific request. It has a time spans of roughly 8min.
        refresh_token : str
            Its a token which lives for longer and can be used to create new tokens.
        api_url : str
            URL to the backend
        base_url : str
            URL to the backend TODO remove this and generate it from api_url
        projects_dir : Path
            Path where the client should be initialized from (aka the root path)
        """
        self.token = token
        self.refresh_token = refresh_token
        self.url = api_url
        self.base_url = base_url
        self.team = None
        # TODO: read this from config
        self.projects_dir = projects_dir

    def get(self, endpoint: str, retry: bool = False, raw: bool = False):
        """Get something from the server trough HTTP

        Parameters
        ----------
        endpoint : str
            Recipient of the HTTP operation
        retry : bool
            Retry to perform the operation. Set to False on recursive calls.
        raw : bool
            Flag for returning raw response

        Returns
        -------
        dict
        Dictionary which contains the server response
        """
        self.ensure_authenticated()
        response = requests.get(urljoin(self.url, endpoint), headers=self._get_headers())

        if response.status_code == 401 and retry:
            self._refresh_access_token()
            return self.get(endpoint=endpoint, retry=False)

        if response.status_code != 200:
            print(
                f"Client get request response ({response.json()}) with unexpected status "
                f"({response.status_code}). "
                f"Client: ({self})"
                f"Request: (endpoint={endpoint})"
            )

        if raw:
            return response
        return response.json()

    def put(self, endpoint: str, payload: Dict, retry: bool = False):
        """Put something on the server trough HTTP

        Parameters
        ----------
        endpoint : str
            Recipient of the HTTP operation
        payload : dict
            What you want to put on the server (typically json encoded)
        retry : bool
            Retry to perform the operation. Set to False on recursive calls.


        Returns
        -------
        dict
        Dictionary which contains the server response
        """
        self.ensure_authenticated()
        response = requests.put(
            urljoin(self.url, endpoint), json=payload, headers=self._get_headers()
        )

        if response.status_code == 401 and retry:
            self._refresh_access_token()
            return self.put(endpoint=endpoint, payload=payload, retry=False)
        if response.status_code == 429:
            error_code = response.json()["errors"]["code"]
            if error_code == "INSUFFICIENT_REMAINING_STORAGE":
                raise InsufficientStorage()

        if response.status_code != 200:
            print(
                f"Client put request response ({response.json()}) with unexpected status "
                f"({response.status_code}). "
                f"Client: ({self})"
                f"Request: (endpoint={endpoint}, payload={payload})"
            )
        return response.json()

    def post(
            self,
            endpoint: str,
            payload: Optional[Dict] = None,
            retry: bool = False,
            refresh: bool = False,
            error_handlers: Optional[list] = None,
    ):
        """Post something new on the server trough HTTP

        Parameters
        ----------
        endpoint : str
            Recipient of the HTTP operation
        payload : dict
            What you want to put on the server (typically json encoded)
        retry : bool
            Retry to perform the operation. Set to False on recursive calls.
        refresh : bool
            Flag for use the refresh token instead
        error_handlers : list
            List of error handlers

        Returns
        -------
        dict
        Dictionary which contains the server response
        """
        if payload is None:
            payload = {}
        if error_handlers is None:
            error_handlers = []
        self.ensure_authenticated()
        response = requests.post(
            urljoin(self.url, endpoint), json=payload, headers=self._get_headers(refresh=refresh)
        )

        if response.status_code == 401 and retry:
            self._refresh_access_token()
            return self.post(endpoint, payload=payload, retry=False)

        if response.status_code != 200:
            for error_handler in error_handlers:
                error_handler(response.status_code, response.json())
            print(
                f"Client post request response ({response.json()}) with unexpected status "
                f"({response.status_code}). "
                f"Client: ({self})"
                f"Request: (endpoint={endpoint}, payload={payload})"
            )
        return response.json()

    def list_teams(self):
        """Returns a list of all available teams

        Returns
        -------
        list[Team]
        Available teams
        """
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

    def current_team(self) -> Team:
        """Returns the currently selected team

        Returns
        -------
        Team
        Currently selected team
        """
        data = self.get("/users/token_info")["selected_team"]
        return Team(id=data["id"], name=data["name"], slug=data["slug"], selected=True)

    def set_team(self, slug: str):
        """Select a team

        Parameters
        ----------
        slug : str
            Slug of the team to select

        Returns
        -------

        """
        matching_team = [team for team in self.list_teams() if team.slug == slug]
        if not matching_team:
            raise NotFound
        data = self.post("/users/select_team", {"team_id": matching_team[0].id}, refresh=True)
        self.token = data["token"]
        self.refresh_token = data["refresh_token"]

    def list_local_datasets(self) -> Iterator[Path]:
        """Returns a list of all local folders who are detected as dataset.

        Returns
        -------
        list[Path]
        List of all local datasets
        """
        for project_path in Path(self.projects_dir).glob("*"):
            if project_path.is_dir() and is_project_dir(project_path):
                yield Path(project_path)

    def list_remote_datasets(self) -> Iterator[RemoteDataset]:
        """Returns a list of all available datasets with the team currently authenticated against

        Returns
        -------
        list[RemoteDataset]
        List of all remote datasets
        """
        for project in self.get("/projects/"):
            yield RemoteDataset(
                name=project["name"],
                slug=project["slug"],
                dataset_id=project["dataset_id"],
                project_id=project["id"],
                image_count=project["num_images"],
                progress=project["progress"],
                client=self,
            )

    def get_remote_dataset(
        self,
        *,
        project_id: Optional[int] = None,
        slug: Optional[str] = None,
        name: Optional[str] = None,
        dataset_id: Optional[int] = None,
    ) -> RemoteDataset:
        """Get a remote dataset based on the parameter passed. You can only choose one of the
        possible parameters and calling this method with multiple ones will result in an
        error.

        Parameters
        ----------
        project_id : int
            ID of the project to return
        slug : str
            Slug of the dataset to return
        name : str
            Name of the dataset to return
        dataset_id : int
            ID of the dataset to return

        Returns
        -------
        RemoteDataset
            Initialized dataset
        """
        num_args = sum(x is not None for x in [name, slug, dataset_id, project_id])
        if num_args > 1:
            raise ValueError(
                f"Too many values provided ({num_args})."
                f" Please choose only 1 way of getting the remote dataset."
            )
        elif num_args == 0:
            raise ValueError(
                f"No values provided. Please select 1 way of getting the remote dataset."
            )
        # TODO: swap project_id for dataset_id when the backend has gotten ride of project_id
        if project_id:
            project = self.get(f"/projects/{project_id}")
            return RemoteDataset(
                name=project["name"],
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
            project = self.get(f"/datasets/{dataset_id}/project")
            return RemoteDataset(
                name=project["name"],
                slug=project["slug"],
                dataset_id=project["dataset_id"],
                project_id=project["id"],
                image_count=project["num_images"],
                progress=project["progress"],
                client=self,
            )

    def create_dataset(self, name: str) -> RemoteDataset:
        """Create a remote dataset

        Parameters
        ----------
        name : str
            Name of the dataset to create

        Returns
        -------
        RemoteDataset
        The created dataset
        """
        project = self.post(
            "/projects",
            {"name": name, "team_id": self.current_team().id},
            error_handlers=[name_taken, validation_error],
        )
        return RemoteDataset(
            name=project["name"],
            slug=project["slug"],
            dataset_id=project["dataset_id"],
            project_id=project["id"],
            image_count=project["num_images"],
            progress=project["progress"],
            client=self,
        )

    def ensure_authenticated(self):
        """Ensure the client is authenticated"""
        if self.refresh_token is not None:
            self._refresh_access_token()

    @classmethod
    def anonymous(cls, projects_dir: Optional[Path] = None):
        """Factory method to create a client with anonymous access privileges.
        This client can only fetch open datasets given their dataset id.

        Parameters
        ----------
        projects_dir : Path
            Path where the client should be initialized from (aka the root path)

        Returns
        -------
        Client
        The inited client
        """
        if not projects_dir:
            projects_dir = Path.home() / ".darwin" / "projects"
        return cls(
            token=None,  # Unauthenticated requests
            refresh_token=None,
            api_url=Client.default_api_url(),
            base_url=Client.default_base_url(),
            projects_dir=projects_dir,
        )

    @classmethod
    def local(cls):
        """Factory method to use the default configuration file to init the client

        Returns
        -------
        Client
        The inited client
        """
        config_path = Path.home() / ".darwin" / "config.yaml"
        return Client.from_config(config_path)

    @classmethod
    def from_token(cls, token: str, projects_dir: Optional[Path] = None):
        """Factory method to create a client from the token passed as parameter

        Parameters
        ----------
        token : str
            Access token used to auth a specific request. It has a time spans of roughly 8min. to
        projects_dir : Path
            Path where the client should be initialized from (aka the root path)

        Returns
        -------
        Client
        The inited client
        """
        if not projects_dir:
            projects_dir = Path.home() / ".darwin" / "projects"
        return cls(
            token=token,
            refresh_token=None,
            api_url=Client.default_api_url(),
            base_url=Client.default_base_url(),
            projects_dir=projects_dir,
        )

    @classmethod
    def from_config(cls, config_path: Path):
        """Factory method to create a client from the configuration file passed as parameter

        Parameters
        ----------
        config_path : str
            Path to a configuration file to use to create the client

        Returns
        -------
        Client
        The inited client
        """
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
    def login(cls, email: str, password: str, projects_dir: Optional[Path] = None):
        """Factory method to create a client with a Darwin user login

        Parameters
        ----------
        email : str
            Email of the Darwin user to use for the login
        password : str
            Password of the Darwin user to use for the login
        projects_dir : str
            String where the client should be initialized from (aka the root path)

        Returns
        -------
        Client
        The inited client
        """
        if projects_dir is None:
            projects_dir = Path.home() / ".darwin" / "projects"
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
            projects_dir=projects_dir,
        )

    def _refresh_access_token(self):
        """Create and sets a new token"""
        response = requests.get(
            urljoin(self.url, "/refresh"), headers=self._get_headers(refresh=True)
        )
        if response.status_code != 200:
            raise Unauthenticated()

        data = response.json()
        self.token = data["token"]

    def _get_headers(self, refresh: bool = False):
        """Get the headers of the API calls to the backend.

        Parameters
        ----------
        refresh : bool
            Flag to select refresh token or the normal token

        Returns
        -------
        dict
        Contains the Content-Type and Authorization token
        """
        if refresh:
            return {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.refresh_token}",
            }
        else:
            header = {"Content-Type": "application/json"}
            if self.token is not None:
                header["Authorization"] = f"Bearer {self.token}"
            return header

    def __str__(self):
        return (
            f"(Client, token={self.token}, "
            f"refresh_token={self.refresh_token}, "
            f"url={self.url}, "
            f"base_url={self.base_url}, "
            f"team={self.team}, "
            f"projects_dir={self.projects_dir})"
        )

    @staticmethod
    def default_api_url():
        """Returns the default api url"""
        return f"{Client.default_base_url()}/api/"

    @staticmethod
    def default_base_url():
        """Returns the default base url"""
        return os.getenv('DARWIN_BASE_URL', 'https://darwin.v7labs.com')


def name_taken(code, body):
    if code == 422 and body["errors"]["name"][0] == "has already been taken":
        raise NameTaken


def validation_error(code, body):
    if code == 422:
        raise ValidationError(body)
