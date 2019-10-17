import datetime
import os.path
import sys
from pathlib import Path
from typing import List, Optional

import humanize

from darwin.client import Client
from darwin.config import Config
from darwin.exceptions import (
    InvalidLogin,
    MissingConfig,
    NameTaken,
    NotFound,
    Unauthenticated,
    ValidationError,
)
from darwin.table import Table
from darwin.utils import find_files, make_configuration_file, secure_continue_request


def authenticate(email: str, password: str, projects_dir: Path) -> Config:
    """Authenticate user against the server and creates a configuration file for it

    Parameters
    ----------
    email : str
        Email to use for the client login
    password : str
        Password to use for the client login
    projects_dir : Path
         String where the client should be initialized from

    Returns
    -------
    Config
    A configuration object to handle YAML files
    """
    # Resolve the home folder if the project_dir starts with ~ or ~user
    projects_dir = Path(os.path.expanduser(str(projects_dir)))
    Path(projects_dir).mkdir(parents=True, exist_ok=True)
    print(f"Projects directory created {projects_dir}")

    try:
        client = Client.login(email=email, password=password, projects_dir=projects_dir)
        config_path = Path.home() / ".darwin" / "config.yaml"
        config_path.parent.mkdir(exist_ok=True)
        return make_configuration_file(client)

    except InvalidLogin:
        _error("Invalid credentials")


def current_team():
    """Print the team currently authenticated against"""
    client = _load_client()
    team = client.current_team()
    print(f"{team.slug}")


def list_teams():
    """Print a table of teams to which the client belong to"""
    client = _load_client()
    teams = client.list_teams()
    table = Table(["slug", "full name"], [Table.L, Table.L])
    for team in teams:
        if team.selected:
            table.add_row({"slug": f"(*) {team.slug}", "full name": team.name})
        else:
            table.add_row({"slug": team.slug, "full name": team.name})
    print(table)


def set_team(team_slug: str):
    """Switches the client to the selected team and persist the change on the configuration file

    Parameters
    ----------
    team_slug : str
        Slug of the team to switch to
    """
    client = _load_client()
    try:
        client.set_team(slug=team_slug)
    except NotFound:
        _error(f"Unknown team '{team_slug}'")
    config_path = Path.home() / ".darwin" / "config.yaml"
    config = Config(config_path)
    config.write("token", client.token)
    config.write("refresh_token", client.refresh_token)


def create_dataset(name: str):
    """Creates a project remotely"""
    client = _load_client(offline=False)
    try:
        dataset = client.create_dataset(name=name)
        print(f"Dataset '{dataset.name}' has been created.\nAccess at {dataset.remote_path}")
    except NameTaken:
        _error(f"Dataset name '{name}' is already taken.")
    except ValidationError:
        _error(f"Dataset name '{name}' is not valid.")


def local():
    """Lists synced projects, stored in the specified path. """
    table = Table(["name", "images", "sync date", "size"], [Table.L, Table.R, Table.R, Table.R])
    client = _load_client(offline=True)
    for project_path in client.list_local_datasets():
        table.add_row({
            'name': project_path.name,
            'images': sum(1 for _ in find_files(project_path)),
            'sync_date': humanize.naturaldate(
                datetime.datetime.fromtimestamp(project_path.stat().st_mtime)
            ),
            'size': humanize.naturalsize(
                sum(p.stat().st_size for p in find_files(project_path))
            )
        })
    print(table)


def path(dataset_slug: str) -> Path:
    """Returns the absolute path of the specified project, if synced"""
    client = _load_client(offline=True)
    try:
        for p in client.list_local_datasets():
            if dataset_slug == p.name:
                return p
    except NotFound:
        _error(f"Project '{dataset_slug}' does not exist locally. "
               f"Use 'darwin remote' to see all the available projects, "
               f"and 'darwin pull' to pull them.")


def url(project_slug: str) -> Path:
    """Returns the url of the specified project"""
    client = _load_client(offline=True)
    try:
        remote_dataset = client.get_remote_dataset(slug=project_slug)
        return remote_dataset.remote_path
    except NotFound:
        _error(f"Project '{project_slug}' does not exist.")



def pull_project(project_slug: str):
    """Downloads a remote project (images and annotations) in the projects directory. """
    client = _load_client()
    try:
        dataset = client.get_remote_dataset(slug=project_slug)
        print(f"Pulling project {project_slug}:latest")
        dataset.pull()
        return dataset
    except NotFound:
        _error(f"project '{project_slug}' does not exist at {client.url}. "
               f"Use 'darwin remote' to list all the remote projects.")
    except Unauthenticated:
        _error(f"please re-authenticate")


def remote():
    """Lists remote projects with its annotation progress"""
    client = _load_client()
    # TODO: add listing open datasets
    table = Table(["name", "images", "progress", "id"], [Table.L, Table.R, Table.R, Table.R])
    for dataset in client.list_remote_datasets():
        table.add_row(
            {
                "name": dataset.slug,
                "images": dataset.image_count,
                "progress": f"{round(dataset.progress*100,1)}%",
                "id": dataset.project_id,
            }
        )
    if len(table) == 0:
        print("No projects available.")
    else:
        print(table)


def remove_remote_project(project_slug: str):
    """Remove a remote project from the workview. The project gets archived. """
    client = _load_client(offline=False)
    try:
        dataset = client.get_remote_dataset(slug=project_slug)
        print(f"About to delete {dataset.name} on darwin.")
        if not secure_continue_request():
            print("Cancelled.")
            return

        dataset.remove()
    except NotFound:
        _error(f"No dataset with name '{project_slug}'")


def upload_data(
        project_slug: str,
        files: Optional[List[str]],
        extensions_to_exclude: Optional[List[str]],
        fps: Optional[int],
):
    """Uploads the files provided as parameter to the remote dataset selected

    Parameters
    ----------
    project_slug : str
        Slug of the project to retrieve
    files : list[str]
        List of files to upload. Can be None.
    extensions_to_exclude : list[str]
        List of extension to exclude from the file scan (which is done only if files is None)
    fps : int
        Number of files per second to upload
    """
    client = _load_client()
    try:
        dataset = client.get_remote_dataset(slug=project_slug)
        dataset.push(extensions_to_exclude=extensions_to_exclude, fps=fps, files_to_upload=files)
    except NotFound:
        _error(f"No dataset with name '{project_slug}'")



def _error(message):
    print(f"Error: {message}")
    sys.exit(1)


def _load_client(offline: bool = False):
    """Fetches a client, potentially offline

    Parameters
    ----------
    offline : bool
        Flag for using an offline client

    Returns
    -------
    Client
    The client requested
    """
    try:
        client = Client.default()
        if not offline:
            client.ensure_authenticated()
        return client
    except MissingConfig:
        _error("Authenticate first")
    except InvalidLogin:
        _error("Please re-authenticate")
    except Unauthenticated:
        _error("Please re-authenticate")