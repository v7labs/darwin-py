from re import MULTILINE, compile

PYPROJECT_VERSION_REGEX = compile(r"^version\s?=\s?\"(\d+\.\d+\.\d+)\"", flags=MULTILINE)
SEMVER_REGEX = compile(r"^\d+\.\d+\.\d+$")
SEMVER_SEGMENT = compile(r"^\d+$")
