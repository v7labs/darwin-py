import os.path
import sys
from pathlib import Path
from typing import List

import humanize
from tqdm import tqdm

from darwin.client import Client
from darwin.config import Config
from darwin.dataset import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS
from darwin.exceptions import (
    InvalidLogin,
    MissingConfig,
    NameTaken,
    NotFound,
    Unauthenticated,
    ValidationError,
)
from darwin.table import Table


def error(message):
    print(f"Error: {message}")
    sys.exit(1)


def load_client(offline: bool = False):
    try:
        client = Client.default()
        if not offline:
            client._ensure_authenticated()
        return client
    except MissingConfig:
        error("Authenticate first")
    except InvalidLogin:
        error("Please re-authenticate")
    except Unauthenticated:
        error("Please re-authenticate")


def authenticate(email: str, password: str, projects_dir: str) -> Config:
    """Authenticate user. """
    projects_dir = os.path.expanduser(projects_dir)
    try:
        client = Client.login(email=email, password=password)
    except InvalidLogin:
        error("Invalid credentials")
    config_path = Path.home() / ".darwin" / "config.yaml"
    config_path.parent.mkdir(exist_ok=True)

    default_config = {
        "token": client._token,
        "refresh_token": client._refresh_token,
        "api_endpoint": client._url,
        "base_url": client._base_url,
        "projects_dir": projects_dir,
    }

    Path(projects_dir).mkdir(parents=True, exist_ok=True)
    print(f"Projects directory created {projects_dir}")
    return Config(config_path, default_config)


def current_team():
    client = load_client()
    team = client.current_team()
    print(f"{team.slug}")


def list_teams():
    client = load_client()
    teams = client.list_teams()
    table = Table(["slug", "full name"], [Table.L, Table.L])
    for team in teams:
        if team.selected:
            table.add_row({"slug": f"(*) {team.slug}", "full name": team.name})
        else:
            table.add_row({"slug": team.slug, "full name": team.name})
    print(table)


def set_team(team_slug: str):
    client = load_client()
    try:
        client.set_team(slug=team_slug)
    except NotFound:
        error(f"Unknown team '{team_slug}'")
    config_path = Path.home() / ".darwin" / "config.yaml"
    config = Config(config_path)
    config.write("token", client._token)
    config.write("refresh_token", client._refresh_token)


def continue_request():
    """Asks for explicit approval from the user. """
    approval = input("Do you want to continue? [Y/n] ")
    if approval not in ["Y", "y", ""]:
        return False
    return True


def secure_continue_request():
    """Asks for explicit approval from the user. """
    approval = input("Do you want to continue? [y/N] ")
    if approval not in ["Y", "y"]:
        return False
    return True


def create_dataset(dataset_name: str):
    """Creates a project remotely. """

    client = load_client(offline=False)

    try:
        dataset = client.create_dataset(name=dataset_name)
    except NameTaken:
        error(f"Dataset name '{dataset_name}' is already taken.")
    except ValidationError:
        error(f"Dataset name '{dataset_name}' is not valid.")

    print(f"Dataset '{dataset_name}' has been created.\nAccess at {dataset.url}")


def local():
    """Lists synced projects, stored in the specified path. """
    table = Table(["name", "images", "sync date", "size"], [Table.L, Table.R, Table.R, Table.R])
    client = load_client(offline=True)
    for dataset in client.list_local_datasets():
        table.add_row(
            {
                "name": dataset.name,
                "images": dataset.image_count,
                "sync date": humanize.naturaldate(dataset.sync_date),
                "size": humanize.naturalsize(dataset.disk_size),
            }
        )
    print(table)


def path(project_slug: str) -> Path:
    """Returns the absolute path of the specified project, if synced"""
    client = load_client(offline=True)
    try:
        local_dataset = client.get_local_dataset(slug=project_slug)
    except NotFound:
        error(
            f"Project '{project_slug}' does not exist locally. Use 'darwin remote' to see all the available projects, and 'darwin pull' to pull them."
        )
    return local_dataset.project_path


def url(project_slug: str) -> Path:
    """Returns the url of the specified project"""
    client = load_client(offline=True)
    try:
        remote_dataset = client.get_remote_dataset(slug=project_slug)
    except NotFound:
        error(f"Project '{project_slug}' does not exist.")
    return remote_dataset.url


def pull_project(project_slug: str):
    """Downloads a rermote project (images and annotations) in the projects directory. """
    client = load_client()
    try:
        dataset = client.get_remote_dataset(slug=project_slug)
    except NotFound:
        error(
            f"project '{project_slug}' does not exist at {client._url}. Use 'darwin remote' to list all the remote projects."
        )
    except Unauthenticated:
        error(f"please re-authenticate")
    print(f"Pulling project {project_slug}:latest")
    progress, count = dataset.pull()
    for _ in tqdm(progress(), total=count, desc="Downloading"):
        pass

    return dataset.local()


def remote():
    """Lists remote projects with its annotation progress"""
    client = load_client()
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
    client = load_client(offline=False)
    try:
        dataset = client.get_remote_dataset(slug=project_slug)
    except NotFound:
        error(f"No dataset with name '{project_slug}'")

    print(f"About to deleting {dataset.name} on darwin.")
    if not secure_continue_request():
        print("Cancelled.")
        return

    dataset.remove()


def remove_local_project(project_slug: str):
    """Remove a local project from the workview. The project gets archived. """
    client = load_client(offline=False)
    try:
        dataset = client.get_local_dataset(slug=project_slug)
    except NotFound:
        error(f"No dataset with name '{project_slug}'")

    print(f"About to deleting {dataset.name} locally.")
    if not secure_continue_request():
        print("Cancelled.")
        return

    dataset.remove()


def upload_data(
    project_slug: str, files: List[str], extensions_to_exclude: List[str], fps: int, recursive: bool
):
    client = load_client()
    try:
        dataset = client.get_remote_dataset(slug=project_slug)
    except NotFound:
        error(f"No dataset with name '{project_slug}'")

    files_to_upload: List[Path] = []
    try:
        for path in files:
            files_to_upload += find_files(Path(path), recursive, extensions_to_exclude)
    except FileNotFoundError as fnf:
        error(f"File '{fnf.filename}' not found")

    if not files_to_upload:
        print("No files to upload, check your path and exclusion filters")
        return

    for _ in tqdm(
        dataset.upload_files(files_to_upload, fps=fps), total=len(files_to_upload), desc="Uploading"
    ):
        pass


def find_files(root: Path, recursive: bool, exclude: List[str]) -> List[Path]:
    if not root.is_dir():
        if (
            root.suffix in SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS
            and root.suffix not in exclude
        ):
            return [root]
        else:
            return []

    files: List[Path] = []
    for file in root.iterdir():
        if file.is_dir():
            if recursive:
                files += find_files(file, recursive, exclude)
        else:
            if (
                file.suffix in SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS
                and file.suffix not in exclude
            ):
                files += [file]
    return files
