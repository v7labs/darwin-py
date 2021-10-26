from pathlib import PurePosixPath
from typing import Optional, Tuple

from datatypes import PathLike


def construct_full_path(remote_path: Optional[str], filename: str) -> PathLike:
    if remote_path is None:
        return filename
    else:
        return (PurePosixPath("/") / remote_path / filename).as_posix()


def deconstruct_full_path(filename: str) -> Tuple[str, str]:
    posix_path = PurePosixPath("/") / filename
    return str(posix_path.parent), posix_path.name
