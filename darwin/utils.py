from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from darwin.config import Config

SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpeg", ".jpg", ".jfif", ".tif"]
SUPPORTED_VIDEO_EXTENSIONS = [".bpm", ".mov", ".mp4"]
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS


def is_extension_allowed(extension):
    return extension.lower() in SUPPORTED_EXTENSIONS


def is_image_extension_allowed(extension):
    return extension.lower() in SUPPORTED_IMAGE_EXTENSIONS


def is_video_extension_allowed(extension):
    return extension.lower() in SUPPORTED_VIDEO_EXTENSIONS


if TYPE_CHECKING:
    from darwin.client import Client


def urljoin(*parts: str) -> str:
    """Take as input an unpacked list of strings and joins them to form an URL"""
    return "/".join(part.strip("/") for part in parts)


def is_project_dir(project_path: Path) -> bool:
    """Verifies if the directory is a project from Darwin by inspecting its sturcture

    Parameters
    ----------
    project_path : Path
        Directory to examine

    Returns
    -------
    bool
        Is the directory a project from Darwin?
    """
    return (project_path / "releases").exists() and (project_path / "images").exists()


def is_deprecated_project_dir(project_path: Path) -> bool:
    """Verifies if the directory is a project from Darwin that uses a deprectated local structure

    Parameters
    ----------
    project_path : Path
        Directory to examine

    Returns
    -------
    bool
        Is the directory a project from Darwin?
    """
    return (project_path / "annotations").exists() and (project_path / "images").exists()


def prompt(msg: str, default: Optional[str] = None) -> str:
    """Prompt the user on a CLI to input a message

    Parameters
    ----------
    msg : str
        Message to print
    default : str
        Default values which is put between [] when the user is prompted

    Returns
    -------
    str
    The input from the user or the default value provided as parameter if user does not provide one
    """
    if default:
        msg = f"{msg} [{default}]: "
    else:
        msg = f"{msg}: "
    result = input(msg)
    if not result and default:
        return default
    return result


def find_files(
    files: List[Union[str, Path]] = [], recursive: bool = True, files_to_exclude: List[Union[str, Path]] = [],
) -> List[Path]:
    """Retrieve a list of all files belonging to supported extensions. The exploration can be made
    recursive and a list of files can be excluded if desired.

    Parameters
    ----------
    files: List[Union[str, Path]]
        List of files that will be filtered with the supported file extensions and returned
    recursive : bool
        Flag for recursive search
    files_to_exclude : List[Union[str, Path]]
        List of files to exclude from the search

    Returns
    -------
    list[Path]
    List of all files belonging to supported extensions. Can't return None.
    """

    # Init the return value
    found_files = []
    pattern = "**/*" if recursive else "*"

    for path in map(Path, files):
        if path.is_dir():
            found_files.extend([f for f in path.glob(pattern) if is_extension_allowed(f.suffix)])
        elif is_extension_allowed(path.suffix):
            found_files.append(path)

    # Filter the list and return it
    files_to_exclude = set(files_to_exclude)
    return [f for f in found_files if f.name not in files_to_exclude and str(f) not in files_to_exclude]


def secure_continue_request() -> bool:
    """Asks for explicit approval from the user. Empty string not accepted"""
    return input("Do you want to continue? [y/N] ") in ["Y", "y"]


def persist_client_configuration(
    client: "Client", default_team: Optional[str] = None, config_path: Optional[Path] = None
) -> Config:
    """Authenticate user against the server and creates a configuration file for it

    Parameters
    ----------
    client : Client
        Client to take the configurations from
    config_path : Path
        Optional path to specify where to save the configuration file

    Returns
    -------
    Config
    A configuration object to handle YAML files
    """
    if not config_path:
        config_path = Path.home() / ".darwin" / "config.yaml"
        config_path.parent.mkdir(exist_ok=True)

    team_config = client.config.get_default_team()
    config = Config(config_path)
    config.set_team(
        team=team_config["slug"], api_key=team_config["api_key"], datasets_dir=team_config["datasets_dir"],
    )
    config.set_global(api_endpoint=client.url, base_url=client.base_url, default_team=default_team)

    return config
