from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from darwin.datatypes import Property


def construct_full_path(remote_path: Optional[str], filename: str) -> str:
    """
    Returns the full Darwin path (in Posix form) of the given file, is such exists.

    Parameters
    ----------
    remote_path : Optional[str]
        The remote path to this file, if it exists.
    filename : str
        The name of the file.

    Returns
    -------
    str
        The full Darwin path of the file in Posix form.
    """
    if remote_path is None:
        return filename
    else:
        return (PurePosixPath("/") / remote_path / filename).as_posix()


def deconstruct_full_path(filename: str) -> Tuple[str, str]:
    """
    Returns a tuple with the parent folder of the file and the file's name.

    Parameters
    ----------
    filename : str
        The path (with filename) that will be deconstructed.

    Returns
    -------
    Tuple[str, str]
        A tuple where the first element is the path of the parent folder, and the second is the
        file's name.
    """
    posix_path = PurePosixPath("/") / filename
    return str(posix_path.parent), posix_path.name


def parse_manifest(path: Path) -> list[Property]:
    """
    Parses the given manifest and returns a list of all the properties in it.

    Parameters
    ----------
    path : str
        The path to the manifest.

    Returns
    -------
    list[Property]
        A list of all the properties in the given manifest.
    """
    with open(path) as f:
        manifest = json.load(f)

    properties = []
    for m_cls in manifest.get("classes"):
        for property in m_cls["properties"]:
            properties.append(Property(**property))

    return properties


def is_properties_enabled(path: Path) -> bool:
    """
    Returns whether the properties feature is enabled in the given manifest.

    Parameters
    ----------
    manifest : list[dict]
        The manifest to check.

    Returns
    -------
    bool
        Whether the properties feature is enabled in the given manifest.
    """
    return bool(parse_manifest(path))


def split_paths_by_manifest(path: Path) -> tuple[Path, list[Property] | Path]:
    """
    Returns a tuple with the given path and the properties of the manifest of the given path.

    Parameters
    ----------
    path : Path
        The path to split.

    Returns
    -------
    tuple[Path, Optional[list[Property]]]
        A tuple with the given path and the properties of the manifest of the given path.
    """
    properties = parse_manifest(path)
    if not properties:
        return path, path

    return path, properties
