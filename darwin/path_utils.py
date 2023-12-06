from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple


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


def parse_manifest(path: Path) -> dict:
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

    return manifest


def is_properties_enabled(
    export_dir_path: Path,
    dir: str = ".v7",
    filename: str = "manifest.json",
    annotations_dir: str = "annotations",
) -> bool:
    """
    Returns whether the given export directory has properties enabled.

    Parameters
    ----------
    export_dir_path : Path
        The path to the export directory.

    Returns
    -------
    bool
        Whether the given export directory has properties enabled.
    """
    path = export_dir_path / dir
    if not path.exists():
        annotations_path = export_dir_path / annotations_dir
        for annotation_path in annotations_path.rglob("*"):
            with open(annotation_path) as f:
                if '"properties"' in f.read():
                    return True
        return False

    manifest_path = path / filename
    manifest_classes = parse_manifest(manifest_path).get("classes", [])
    return any(_cls.get("properties") for _cls in manifest_classes)
