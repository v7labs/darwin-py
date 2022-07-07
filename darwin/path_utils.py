from pathlib import PurePosixPath
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
