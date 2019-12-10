import os
from pathlib import Path
from typing import Dict, Iterator, Optional

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
    Unauthorized,
    ValidationError,
)
from darwin.utils import is_project_dir, urljoin


class Client:
    def __init__(
        self,
        team: Optional[str],
        api_key: Optional[str],
        api_url: str,
        base_url: str,
        datasets_dir: Path,
    ):
        """Initializes a Client object. Clients are responsible for holding the logic and for
        interacting with the remote hosts.

        Parameters
        ----------
        api_key : str
            Access token used to auth a specific request. It has a time spans of roughly 8min.
        api_url : str
            URL to the backend
        base_url : str
            URL to the backend TODO remove this and generate it from api_url
        datasets_dir : Path
            Path where the client should be initialized from (aka the root path)
        """
        self.api_key = api_key
        self.url = api_url
        self.base_url = base_url
        self.team = team
        # TODO: read this from config
        self.datasets_dir = datasets_dir

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
        response = requests.get(urljoin(self.url, endpoint), headers=self._get_headers())

        if response.status_code == 401:
            raise Unauthorized()
        # if response.status_code != 200:
        #     print(
        #         f"Client get request response ({response.json()}) with unexpected status "
        #         f"({response.status_code}). "
        #         f"Client: ({self})"
        #         f"Request: (endpoint={endpoint})"
        #     )
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
        response = requests.put(
            urljoin(self.url, endpoint), json=payload, headers=self._get_headers()
        )

        if response.status_code == 401:
            raise Unauthorized()

        if response.status_code == 429:
            error_code = response.json()["errors"]["code"]
            if error_code == "INSUFFICIENT_REMAINING_STORAGE":
                raise InsufficientStorage()

        # if response.status_code != 200:
        #     print(
        #         f"Client put request response ({response.json()}) with unexpected status "
        #         f"({response.status_code}). "
        #         f"Client: ({self})"
        #         f"Request: (endpoint={endpoint}, payload={payload})"
        #     )
        return response.json()

    def post(
        self,
        endpoint: str,
        payload: Optional[Dict] = None,
        retry: bool = False,
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
        response = requests.post(
            urljoin(self.url, endpoint), json=payload, headers=self._get_headers()
        )
        if response.status_code == 401:
            raise Unauthorized()

        # if response.status_code != 200:
        #     for error_handler in error_handlers:
        #         error_handler(response.status_code, response.json())
        #     print(
        #         f"Client post request response ({response.json()}) with unexpected status "
        #         f"({response.status_code}). "
        #         f"Client: ({self})"
        #         f"Request: (endpoint={endpoint}, payload={payload})"
        #     )
        return response.json()

    def list_local_datasets(self) -> Iterator[Path]:
        """Returns a list of all local folders who are detected as dataset.

        Returns
        -------
        list[Path]
        List of all local datasets
        """
        for project_path in Path(self.datasets_dir).glob("*"):
            if project_path.is_dir() and is_project_dir(project_path):
                yield Path(project_path)

    def list_remote_datasets(self) -> Iterator[RemoteDataset]:
        """Returns a list of all available datasets with the team currently authenticated against

        Returns
        -------
        list[RemoteDataset]
        List of all remote datasets
        """
        for dataset in self.get("/datasets/"):
            yield RemoteDataset(
                name=dataset["name"],
                slug=dataset["slug"],
                team=self.team,
                dataset_id=dataset["id"],
                image_count=dataset["num_images"],
                progress=dataset["progress"],
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
        dataset = self.post(
            "/datasets", {"name": name}, error_handlers=[name_taken, validation_error]
        )
        return RemoteDataset(
            name=dataset["name"],
            team=self.team,
            slug=dataset["slug"],
            dataset_id=dataset["id"],
            image_count=dataset["num_images"],
            progress=dataset["progress"],
            client=self,
        )

    @classmethod
    def anonymous(cls, datasets_dir: Optional[Path] = None):
        """Factory method to create a client with anonymous access privileges.
        This client can only fetch open datasets given their dataset id.

        Parameters
        ----------
        datasets_dir : Path
            Path where the client should be initialized from (aka the root path)

        Returns
        -------
        Client
        The inited client
        """
        if not datasets_dir:
            datasets_dir = Path.home() / ".darwin" / "projects"
        return cls(
            token=None,  # Unauthenticated requests
            refresh_token=None,
            api_url=Client.default_api_url(),
            base_url=Client.default_base_url(),
            datasets_dir=datasets_dir,
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
    def from_token(cls, token: str, datasets_dir: Optional[Path] = None):
        """Factory method to create a client from the token passed as parameter

        Parameters
        ----------
        token : str
            Access token used to auth a specific request. It has a time spans of roughly 8min. to
        datasets_dir : Path
            Path where the client should be initialized from (aka the root path)

        Returns
        -------
        Client
        The inited client
        """
        if not datasets_dir:
            datasets_dir = Path.home() / ".darwin" / "projects"
        return cls(
            token=token,
            refresh_token=None,
            api_url=Client.default_api_url(),
            base_url=Client.default_base_url(),
            datasets_dir=datasets_dir,
        )

    @classmethod
    def from_config(cls, config_path: Path, team: Optional[str] = None):
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
        if team:
            team_config = config.get_team(team)
        else:
            team_config = config.get_default_team()

        return cls(
            team=team_config["slug"],
            api_key=team_config["api_key"],
            api_url=config.get("global/api_endpoint"),
            base_url=config.get("global/base_url"),
            datasets_dir=config.get("global/datasets_dir"),
        )

    @classmethod
    def login(cls, api_key: str, datasets_dir: Optional[Path] = None):
        """Factory method to create a client with a Darwin user login

        Parameters
        ----------
        email : str
            Email of the Darwin user to use for the login
        password : str
            Password of the Darwin user to use for the login
        datasets_dir : str
            String where the client should be initialized from (aka the root path)

        Returns
        -------
        Client
        The inited client
        """
        if datasets_dir is None:
            datasets_dir = Path.home() / ".darwin" / "projects"
        headers = {"Content-Type": "application/json", "Authorization": f"ApiKey {api_key}"}
        api_url = Client.default_api_url()
        response = requests.get(urljoin(api_url, "/users/token_info"), headers=headers)

        if response.status_code != 200:
            raise InvalidLogin()
        data = response.json()
        team_id = data["selected_team"]["id"]
        team = [team["slug"] for team in data["teams"] if team["id"] == team_id][0]

        return cls(
            api_key=api_key,
            api_url=api_url,
            base_url=Client.default_base_url(),
            team=team,
            datasets_dir=datasets_dir,
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

    def _get_headers(self):
        """Get the headers of the API calls to the backend.

        Parameters
        ----------
     
        Returns
        -------
        dict
        Contains the Content-Type and Authorization token
        """
        header = {"Content-Type": "application/json"}
        if self.api_key is not None:
            header["Authorization"] = f"ApiKey {self.api_key}"
        return header

    def __str__(self):
        return (
            f"(Client, token={self.api_key}, "
            f"url={self.url}, "
            f"base_url={self.base_url}, "
            f"team={self.team}, "
            f"datasets_dir={self.datasets_dir})"
        )

    @staticmethod
    def default_api_url():
        """Returns the default api url"""
        return f"{Client.default_base_url()}/api/"

    @staticmethod
    def default_base_url():
        """Returns the default base url"""
        return os.getenv("DARWIN_BASE_URL", "https://darwin.v7labs.com")


def name_taken(code, body):
    if code == 422 and body["errors"]["name"][0] == "has already been taken":
        raise NameTaken


def validation_error(code, body):
    if code == 422:
        raise ValidationError(body)
