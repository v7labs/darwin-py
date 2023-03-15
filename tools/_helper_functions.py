from pathlib import Path
from re import match

from ._console import TerminalOut
from ._regexes import SEMVER_REGEX, SEMVER_SEGMENT


# Validators
def check_file_exists(path: Path, term: TerminalOut) -> None:
    if path.exists():
        term.success(f"{path.absolute()} found")

    else:
        term.fail(f"[red]ERROR[/red] {path.name} not found")
        exit(40)


def validate_semver_segment(s: str) -> bool:
    return match(SEMVER_SEGMENT, s) is not None


def validate_semver_segment_to_output(s: str, term: TerminalOut) -> str:
    return f"{term.SUCCESS}" if validate_semver_segment(s) else f"{term.FAILURE}"


def validate_major_minor_patch(version: str, term: TerminalOut) -> None:
    term.message("[cyan]Checking version is valid semver[/cyan]")
    if not match(SEMVER_REGEX, version):
        term.success(f"Version is not valid semver: {version}")
        exit(10)

    major, minor, patch = version.split(".")
    for k, v in zip(["Major", "Minor", "Patch"], [major, minor, patch]):
        errors = 0
        message = f"{k} version is set to {v} "
        icon = term.SUCCESS
        if validate_semver_segment(v):
            message += "[green]valid![/green]"
        else:
            message += f"[red]{v} - invalid.[/red]"
            icon = term.FAILURE
            errors += 1

        term.message(message, icon)

    if errors > 0:
        exit(20)


def check_is_at_or_less_than_latest_version(version: str, pypi_version: str, term: TerminalOut) -> None:
    [major, minor, patch] = version.split(".")
    [pypi_major, pypi_minor, pypi_patch] = pypi_version.split(".")

    try:
        assert int(major) >= int(pypi_major)
        assert int(minor) >= int(pypi_minor)
        assert int(patch) >= int(pypi_patch)
    except AssertionError:
        term.fail(f"[red]ERROR[/red] Version is greater than latest version on PyPi")
        exit(60)
    else:
        term.success(f"[green]SUCCESS[/green] version is greater than or equal to latest version on PyPi")

    if int(major) > int(pypi_major):
        term.message(
            f"[red]CAUTION: [/red] You are updating the major version. Please check that you intend to do this.", ""
        )
