from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Optional, Tuple, Union


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
        return PurePosixPath("/", remote_path, filename).as_posix()


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


def parse_metadata(path: Path) -> dict:
    """
    Returns the parsed metadata file.

    Parameters
    ----------
    path : Path
        The path to the metadata file.

    Returns
    -------
    dict
        The parsed metadata file.
    """
    with open(path) as f:
        metadata = json.load(f)

    return metadata


def is_properties_enabled(
    path: Path,
    dir: str = ".v7",
    filename: str = "metadata.json",
    annotations_dir: str = "annotations",
) -> Union[Path, bool]:
    """
    Returns whether the given export directory has properties enabled.

    Parameters
    ----------
    path : Path
        The path to the export directory.
    dir : str, optional
        The name of the .v7 directory, by default ".v7"
    filename : str, optional
        The name of the metadata file, by default "metadata.json"
    annotations_dir : str, optional
        The name of the annotations directory, by default "annotations"

    Returns
    -------
    bool
        Whether the given export directory has properties enabled.
    """
    # If the path is a file, get its parent
    if path.is_file():
        path = path.parent

    # Check if the path has a .v7 directory
    v7_path = path / dir
    if not v7_path.exists():
        # If it doesn't, check if it has an annotations directory
        annotations_path = path / annotations_dir
        if not annotations_path.exists():
            return False

        # If it does, check if any annotation file has "properties" in it
        for annotation_path in annotations_path.rglob("*"):
            with open(annotation_path) as f:
                if '"properties"' in f.read():
                    return True

        # If none of the annotation files have "properties" in them, return False
        return False

    # .v7 directory exists, parse the metadata file and check if any class has properties
    # Additionally check if there are any item-level properties
    metadata_path = v7_path / filename
    metadata = parse_metadata(metadata_path)
    metadata_classes = metadata.get("classes", [])
    metadata_item_level_properties = metadata.get("properties", [])
    for _cls in metadata_classes:
        if _cls.get("properties"):
            return metadata_path
    for _item_level_property in metadata_item_level_properties:
        if _item_level_property.get("property_values"):
            return metadata_path

    return False
