import os
from typing import Optional

def construct_full_path(remote_path: Optional[str], filename: str) -> str:
    if remote_path is None:
        return filename
    else:
        return os.path.join("/", remote_path, filename)
