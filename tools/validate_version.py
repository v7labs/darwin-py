#!/usr/bin/env python3

from argparse import ArgumentParser
from importlib import import_module
from pathlib import Path
from re import search

from requests import get
from rich.panel import Panel
from rich_argparse import RichHelpFormatter

from tools._console import TerminalOut
from tools._helper_functions import (
    check_file_exists,
    check_is_at_or_less_than_latest_version,
    validate_major_minor_patch,
)
from tools._regexes import PYPROJECT_VERSION_REGEX

parser = ArgumentParser(
    prog="Darwin-py version validator",
    formatter_class=RichHelpFormatter,
)
parser.add_argument("--ci", action="store_true", help="Run in CI mode (no emojis or colour")

args = parser.parse_args()

term = TerminalOut()


# Paths
path_to_here = Path(__file__).parent
path_to_pyproject = (path_to_here / ".." / "pyproject.toml").resolve()
path_to_version = (path_to_here / ".." / "darwin" / "version" / "__init__.py").resolve()


# Setup term
panel = Panel.fit(
    "[cyan]Darwin-py version validator[/cyan]\n[white]✔ Confirms all versions of Darwin-py match and are valid[/white]"
)
term.console.print(panel)

# Check version matches in toml and python
term.section("Checking pyproject.toml")

check_file_exists(path_to_pyproject, term)

with path_to_pyproject.open("r") as f:
    pyproject_toml = f.read()
    pyproject_version_match = search(PYPROJECT_VERSION_REGEX, pyproject_toml)

if not pyproject_version_match:
    term.fail(f"[red]ERROR[/red] version not found in pyproject.toml")
    exit(2)

pyproject_version = pyproject_version_match.group(1)
term.message(f"Found version: [green]{pyproject_version}[/green]")
validate_major_minor_patch(pyproject_version, term)

term.newline()

# Check version in darwin module
term.section("Checking darwin/version.py")

term.message(f"Using {path_to_version} as version file")
check_file_exists(path_to_version, term)
try:
    version_module = import_module("darwin.version")
except ImportError:
    term.fail(f"[red]ERROR[/red] darwin.version module not found")
    exit(3)
else:
    term.success(f"Found version: [green]{version_module.__version__}[/green]")

validate_major_minor_patch(version_module.__version__, term)
term.newline()

# Check version in Pypi
term.section("Checking PyPi")
package = get("https://pypi.org/pypi/darwin-py/json")
if not package.ok:
    term.fail(f"[red]ERROR[/red] Could not get package info from PyPi - cannot check version published")
    exit(4)

package_info = package.json()
latest_version = package_info.get("info", {}).get("version")

if latest_version is None:
    term.message("Could not find latest version on PyPi")
    exit(5)

term.message(f"Latest version on PyPi: [green]{latest_version}[/green]")
validate_major_minor_patch(latest_version, term)
term.newline()


# Compare versions
term.section("Comparing versions")
if version_module.__version__ == pyproject_version:
    term.message(f"[green]SUCCESS[/green] version in pyproject.toml and darwin/version.py match ")
else:
    term.message(f"[red]ERROR[/red] version in pyproject.toml and darwin/version.py do not match ")
    term.message(f"pyproject.toml version: [green]{pyproject_version}[/green]")
    term.message(f"darwin/version.py version: [red]{version_module.__version__}[/red]")
    exit(5)

check_is_at_or_less_than_latest_version(version_module.__version__, latest_version, term)

term.message(f"[green]SUCCESS[/green] Version is valid across version file, pyproject.toml, and Pypi.org")


exit(0)
