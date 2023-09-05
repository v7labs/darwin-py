#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from os import environ
from pathlib import Path
from pprint import pprint
from typing import Tuple

from requests import get
from toml import dumps, loads
from validate_pyproject import api as pyproject_api
from validate_pyproject import errors as pyproject_errors

DARWIN_PYPI_INFO_PAGE = environ.get("PYPY_INFO_PAGE", "https://pypi.org/pypi/darwin-py/json")


@dataclass
class Version:
    major: int
    minor: int
    patch: int

    _changed = False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return (
            (self.major == other.major)
            and (self.minor == other.minor)
            and (self.patch > other.patch)
            or (self.major == other.major)
            and (self.minor > other.minor)
            and (self.patch >= other.patch)
            or (self.major > other.major)
            and (self.minor >= other.minor)
            and (self.patch >= other.patch)
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return (
            (self.major == other.major)
            and (self.minor == other.minor)
            and (self.patch < other.patch)
            or (self.major == other.major)
            and (self.minor < other.minor)
            and (self.patch <= other.patch)
            or (self.major < other.major)
            and (self.minor <= other.minor)
            and (self.patch <= other.patch)
        )

    def __sub__(self, other: object) -> Tuple[int, int, int]:
        if not isinstance(other, Version):
            return NotImplemented

        return (
            int(abs(self.major - other.major)),
            int(abs(self.minor - other.minor)),
            int(abs(self.patch - other.patch)),
        )

    def copy(self) -> "Version":
        return Version(self.major, self.minor, self.patch)

    def was_changed(self) -> bool:
        return self._changed

    def increment_major(self) -> None:
        self.major += 1
        self._changed = True

    def increment_minor(self) -> None:
        self.minor += 1
        self._changed = True

    def increment_patch(self) -> None:
        self.patch += 1
        self._changed = True

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def confirm(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/n]: ").lower().strip()
        if answer in ["y", "yes"]:
            return True
        elif answer in ["n", "no"]:
            return False
        else:
            print("Invalid input, type 'y' or 'n'")


def _get_version() -> Version:
    from darwin.version import __version__

    major, minor, patch = __version__.split(".")

    if not major or not minor or not patch:
        raise ValueError("Version not found in darwin.version module")

    return Version(int(major), int(minor), int(patch))


def _get_pyproject_version() -> Version:
    pyproject_dir = Path(__file__).parent.parent
    pyproject_file = pyproject_dir / "pyproject.toml"

    if not pyproject_file.exists():
        raise FileNotFoundError("pyproject.toml not found")

    with open(pyproject_file, "r") as f:
        toml_content = loads(f.read())
        version = toml_content["tool"]["poetry"]["version"]

        if not version:
            raise ValueError("Version not found in pyproject.toml")

        major, minor, patch = version.split(".")
        if not major or not minor or not patch:
            raise ValueError("Version not found in pyproject.toml")

        return Version(int(major), int(minor), int(patch))


def _get_pypi_version(force: bool, cicd: bool) -> Version:
    response = get(DARWIN_PYPI_INFO_PAGE)

    if not response.ok:
        print("PYPI connection not available, sanity checking for PyPi unavailable")
        if not force:
            if cicd:
                print("Failed on PYPI check")
                exit(1)

            if not confirm("Continue without PyPi sanity check?"):
                exit(1)

    try:
        version_in_pypi = response.json()["info"]["version"]
    except KeyError:
        raise ValueError("Version not found in PyPI")

    major, minor, patch = version_in_pypi.split(".")
    if not major or not minor or not patch:
        raise ValueError("Version not found in PyPI")

    return Version(int(major), int(minor), int(patch))


def _sanity_check(version: Version, pyproject_version: Version, pypi_version: Version, force: bool) -> None:
    if version != pyproject_version:
        raise ValueError("Version in darwin.version module and pyproject.toml do not match")

    # pypi version should be either equal to or one greater
    difference_between_versions = version - pypi_version
    if difference_between_versions not in [(0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0)]:
        print(f"Version in PyPI is not equal to or one greater than local version: {version} != {pypi_version}")
        print("Your local version is probably too old, check your version number")

        if not force or confirm("Continue with updating version number?"):
            exit(1)

        print("Pypi version was out of date, this was bypassed.")

    print("Versions are in sync, sanity check passed")


VERSION_TEMPLATE = '__version__ = "{}"\n'


def _update_version(new_version: Version) -> None:
    version_file = (Path(__file__).parent / "..").resolve() / "darwin" / "version" / "__init__.py"

    print(f"Updating version in {version_file.absolute()}")
    assert version_file.exists(), "Version file not found"

    with open(version_file, "w") as f:
        f.write(VERSION_TEMPLATE.format(str(new_version)))


def _update_pyproject_version(new_version: Version) -> None:
    pyproject_file = (Path(__file__).parent / "..").resolve() / "pyproject.toml"
    original_content = pyproject_file.read_text()

    print(f"Updating version in {pyproject_file.absolute()}")
    assert pyproject_file.exists(), "pyproject.toml not found"

    with open(pyproject_file, "r") as f:
        toml_content = loads(f.read())

    toml_content["tool"]["poetry"]["version"] = str(new_version)

    with open(pyproject_file, "w") as f:
        f.write(dumps(toml_content))

    # Sanity check
    try:
        validator = pyproject_api.Validator()
        validator(toml_content)
    except pyproject_errors.ValidationError as e:
        print("Error validating pyproject.toml, reverting changes")
        pprint(e)
        with open(pyproject_file, "w") as f:
            f.write(original_content)
        print("Reverted.  Please fix pyproject.toml and try again.")
        exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Increase version number")
    parser.add_argument("-f", "--force", action="store_true", help="force actions, do not ask for confirmation")
    parser.add_argument(
        "-c",
        "--cicd",
        action="store_true",
        help="run in CI/CD mode (no confirmation, assume failure unless --force specified)",
    )

    parser.add_argument("-v", "--version", action="store_true", help="show version number and exit", default=True)
    parser.add_argument("-M", "--major", action="store_true", help="increase major version")
    parser.add_argument("-m", "--minor", action="store_true", help="increase minor version")
    parser.add_argument("-p", "--patch", action="store_true", help="increase patch version")
    parser.add_argument("-N", "--new-version", type=str, help="set new version number (overrides -M, -m, -p)")

    args = parser.parse_args()

    force_actions = False
    cicd_mode = False

    if args.force:
        print("Force mode enabled, no confirmation will be asked")
        force_actions = True

    if args.cicd:
        print("CI/CD mode enabled, no confirmation will be asked")
        cicd_mode = True

    if args.major and args.minor and args.patch:
        print("Cannot increase major, minor and patch at the same time.  Specify only one of these.")
        exit(2)

    # Constants so that these are not mutated by mistake
    LOCAL_VERSION = _get_version()
    PYPROJECT_VERSION = _get_pyproject_version()
    PYPI_VERSION = _get_pypi_version(force_actions, cicd_mode)

    if args.version:
        print(f"Current version in darwin.version module: {str(LOCAL_VERSION)}")
        print(f"Current version in pyproject.toml: {str(PYPROJECT_VERSION)}")
        print(f"Current version in PyPI: {str(PYPI_VERSION)}")

    _sanity_check(LOCAL_VERSION, PYPROJECT_VERSION, PYPI_VERSION, force_actions)

    new_version = LOCAL_VERSION.copy()

    if (args.major or args.minor or args.patch) and args.new_version:
        print("Cannot increase version and set new version at the same time.  Specify only one of these.")
        exit(2)

    if args.new_version:
        print(f"Setting new version to {args.new_version}")
        new_version = Version(*[int(x) for x in args.new_version.split(".")])
        new_version._changed = True
    else:
        if args.major:
            new_version.increment_major()

        if args.minor:
            new_version.increment_minor()

        if args.patch:
            new_version.increment_patch()

    if (
        new_version.was_changed()
        and not cicd_mode
        and (force_actions or confirm(f"Update version from {str(LOCAL_VERSION)} to {str(new_version)}?"))
    ):
        _update_version(new_version)
        _update_pyproject_version(new_version)
        print(f"Version updated successfully to {str(new_version)}")
    else:
        print("Version not updated")


if __name__ == "__main__":
    main()
