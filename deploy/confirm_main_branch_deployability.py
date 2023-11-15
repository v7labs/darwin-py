#!/usr/bin/env python3

import json
import logging
import sys
from datetime import datetime, timezone
from enum import IntFlag, auto
from os import environ
from subprocess import PIPE, Popen
from typing import List, Tuple

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG) if environ.get("DEBUG") else logger.setLevel(
    logging.INFO
)


# Set up default constants
DEFAULT_BRANCH = environ.get("DEFAULT_BRANCH", "master")
DEFAULT_RELEASE_DAY = environ.get("DEFAULT_RELEASE_DAY", "Tuesday")


class ExitCodes(IntFlag):
    """
    Exit codes for the script
    """

    SUCCESS = auto()
    GETTING_LAST_RELEASE_TAG_THREW_EXITCODE = auto()
    COULD_NOT_PARSE_LAST_RELEASE_TAG = auto()
    GETTING_RELEASE_METADATA_THREW_EXITCODE = auto()
    COULD_NOT_PARSE_RELEASE_METADATA = auto()
    UNEXPECTED_STRUCTURE_TO_RELEASE_METADATA = auto()
    GIT_DIFF_THREW_EXITCODE = auto()
    NO_CHANGES_SINCE_LAST_RELEASE = 128


def printl(*args: str) -> None:
    logger.info(" ".join([str(arg) for arg in args]))


def _run_command(command: str, *args: str) -> Tuple[str, int]:
    """
    Runs a command and returns the stdout and stderr
    (similar to subprocess.run but set to PIPE for ease of parsing - needlessly complex in subprocess.run)

    Parameters
    ----------
    command: str
        The command to run, e.g. "ls"
    args: List[str]
        The command to run as a list of strings, e.g. ["-l"]

    Returns
    -------
    Tuple[int, str]
        The stdout and stderr of the command

    """

    process = Popen([command, *args], stdout=PIPE, stderr=PIPE)
    output, error = process.communicate()
    return output.decode("utf-8"), int(process.returncode)


def _exit(message: str, exit_code: ExitCodes) -> str:
    """
    Exits the script with an exit code and message

    Parameters
    ----------
    message: str
        The message to print
    exit_code: ExitCodes
        The exit code to exit with

    """

    logger.error(message)
    exit(exit_code.value)


def _get_most_recent_release_tag() -> str:
    """
    Gets the last release tag from the repo
    """

    output, error = _run_command("gh", "release", "list", "--limit", "1")
    assert error == 0, _exit(
        "Failed to get last release tag",
        ExitCodes.GETTING_LAST_RELEASE_TAG_THREW_EXITCODE,
    )

    release_tag = str(output).split()[0]
    assert release_tag, _exit(
        "No release tag found", ExitCodes.COULD_NOT_PARSE_LAST_RELEASE_TAG
    )

    return release_tag


def _get_most_recent_release_timestamp(release_tag: str) -> Tuple[str, datetime]:
    """
    Gets the last release timestamp from the repo
    """
    output, error = _run_command(
        "gh", "release", "view", release_tag, "--json", "name,publishedAt"
    )
    assert error == 0, _exit(
        "Failed to get last release timestamp",
        ExitCodes.GETTING_RELEASE_METADATA_THREW_EXITCODE,
    )

    json_output = {}
    try:
        json_output = json.loads(output)
    except json.JSONDecodeError:
        _exit(
            "Could not parse release metadata",
            ExitCodes.COULD_NOT_PARSE_RELEASE_METADATA,
        )

    assert "name" in json_output and "publishedAt" in json_output, _exit(
        "Expected release name and timestamp in metadata",
        ExitCodes.UNEXPECTED_STRUCTURE_TO_RELEASE_METADATA,
    )

    return json_output["name"], datetime.fromisoformat(
        json_output["publishedAt"].replace("Z", "+00:00")
    )


def _get_changes_since_last_release(last_release_timestamp: datetime) -> List[str]:
    """
    Gets the changes since the last release
    """
    SECONDS_IN_A_DAY = 86400
    seconds_since_last_release: int = int(
        (
            datetime.utcnow().astimezone(timezone.utc)
            - last_release_timestamp.astimezone(timezone.utc)
        ).total_seconds()  # Whose idea was it to create timedelta.seconds _and_ datetime.total_seconds
    )
    gitref_to_compare = "{}@{{{} seconds ago}}".format(
        DEFAULT_BRANCH, seconds_since_last_release
    )

    print(
        f"It's been {seconds_since_last_release} seconds since the last release, about {int(seconds_since_last_release / SECONDS_IN_A_DAY)} days ago"
    )
    printl(f"Getting changes since {gitref_to_compare}")

    output, error = _run_command(
        "git", "diff", DEFAULT_BRANCH, gitref_to_compare, "--name-only"
    )
    assert error == 0, _exit(
        "Failed to get changes since last release", ExitCodes.GIT_DIFF_THREW_EXITCODE
    )

    files_changed = output.split("\n")

    return [f for f in files_changed if f]


def main() -> None:
    printl("Testing main branch for deployablity")
    printl("This tests whether any changes have been made since last scheduled deploy")

    printl("Getting most recent release tag")
    last_release_tag = _get_most_recent_release_tag()

    printl("Getting last release timestamp")
    last_release_tag, last_release_timestamp = _get_most_recent_release_timestamp(
        last_release_tag
    )

    printl(f"Last release timestamp: {last_release_timestamp}")
    printl(f"Last release tag: {last_release_tag}")

    printl("Getting changes since last release")
    changes_since_last_release = _get_changes_since_last_release(last_release_timestamp)

    if not changes_since_last_release:
        printl("No changes since last release, exiting")
        exit(ExitCodes.NO_CHANGES_SINCE_LAST_RELEASE)

    printl(f"Changes since last release ({len(changes_since_last_release)}):")
    for i, change in enumerate(changes_since_last_release):
        printl(f"  {i}: {change}")

    printl("All done, exiting")
    exit(ExitCodes.SUCCESS)


if __name__ == "__main__":
    main()
