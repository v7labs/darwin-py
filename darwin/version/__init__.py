from os.path import dirname
from pathlib import Path

from toml import load

version_path = Path(dirname(__file__)) / ".." / ".." / "pyproject.toml"

pyproject = load(version_path.resolve())
version = pyproject.get("tool", {}).get("poetry", {}).get("version")

if version is None:
    raise SystemExit("Project file doesn't contain a version")

__version__ = version
