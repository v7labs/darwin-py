from os.path import dirname
from pathlib import Path
from re import MULTILINE, compile, search

MATCH = compile(r"^version\s*=\s* \"(\d+\.\d+\.\d+)\"", flags=MULTILINE)

path_to_pyproject = Path(Path(dirname(__file__)) / ".." / ".." / "pyproject.toml").resolve()

if not path_to_pyproject.exists():
    raise FileExistsError("Could not find pyproject.toml")

with path_to_pyproject.open("r") as f:
    content = f.read()
    version_matches = search(MATCH, content)
    if version_matches:
        version = version_matches.group(1)
    else:
        raise ValueError("Could not find version in pyproject.toml")

__version__ = version
