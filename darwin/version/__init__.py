from re import MULTILINE, compile, search

MATCH = compile(r"^version\s*=\s* \"(\d+\.\d+\.\d+)\"", flags=MULTILINE)

with open("pyproject.toml", "r") as f:
    content = f.read()
    version_matches = search(MATCH, content)
    if version_matches:
        version = version_matches.group(1)
    else:
        raise ValueError("Could not find version in pyproject.toml")

__version__ = version
