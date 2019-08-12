from pathlib import Path
from typing import Optional

SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpeg", ".jpg"]
SUPPORTED_VIDEO_EXTENSIONS = [".bpm", ".mov", ".mp4"]

def urljoin(*parts):
    return "/".join(part.strip("/") for part in parts)


def is_project_dir(project_path: Path) -> bool:
    return (project_path / "annotations").exists() and (project_path / "images").exists()


def prompt(msg: str, default: Optional[str] = None) -> str:
    if default:
        msg = f"{msg} [{default}]: "
    else:
        msg = f"{msg}: "
    result = input(msg)
    if not result and default:
        return default
    return result
