import re
import tempfile
import uuid
from pathlib import Path
from subprocess import run
from time import sleep
from typing import Generator, Optional, Tuple

import pytest
from attr import dataclass
from cv2 import exp

from darwin.exceptions import DarwinException
from e2e_tests.objects import E2EDataset
from e2e_tests.setup_tests import create_random_image


@dataclass
class CLIResult:
    """Wrapper for the result of a CLI command after decoding the stdout and stderr."""

    return_code: int
    stdout: str
    stderr: str


SERVER_WAIT_TIME = 10


def run_cli_command(
    command: str, working_directory: Optional[str] = None, yes: bool = False, server_wait: int = SERVER_WAIT_TIME
) -> CLIResult:
    """
    Run a CLI command and return the return code, stdout, and stderr.

    Parameters
    ----------
    command : str
        The command to run.
    working_directory : str, optional
        The working directory to run the command in.

    Returns
    -------
    Tuple[int, str, str]
        The return code, stdout, and stderr.
    """

    # Do ot allow directory traversal
    if ".." in command or (working_directory and ".." in working_directory):
        raise DarwinException("Cannot pass directory traversal to 'run_cli_command'.")

    if yes:
        command = f"yes Y | {command}"

    if working_directory:
        result = run(
            command,
            cwd=working_directory,
            capture_output=True,
            shell=True,
        )
    else:
        result = run(
            command,
            capture_output=True,
            shell=True,
        )
    sleep(server_wait)  # wait for server to catch up
    try:
        return CLIResult(result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8"))
    except UnicodeDecodeError:
        return CLIResult(result.returncode, result.stdout.decode("cp437"), result.stderr.decode("cp437"))


def format_cli_output(result: CLIResult) -> str:
    return f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}\n"


def assert_cli(
    result: CLIResult,
    expected_return_code: int = 0,
    in_stdout: Optional[str] = None,
    in_stderr: Optional[str] = None,
    expected_stdout: Optional[str] = None,
    expected_stderr: Optional[str] = None,
    inverse: bool = False,
) -> None:
    assert result.return_code == expected_return_code, format_cli_output(result)
    if not inverse:
        if in_stdout:
            assert in_stdout in result.stdout, format_cli_output(result)
        if in_stderr:
            assert in_stderr in result.stderr, format_cli_output(result)
        if expected_stdout:
            assert result.stdout == expected_stdout, format_cli_output(result)
        if expected_stderr:
            assert result.stderr == expected_stderr, format_cli_output(result)
    else:
        if in_stdout:
            assert in_stdout not in result.stdout, format_cli_output(result)
        if in_stderr:
            assert in_stderr not in result.stderr, format_cli_output(result)
        if expected_stdout:
            assert result.stdout != expected_stdout, format_cli_output(result)
        if expected_stderr:
            assert result.stderr != expected_stderr, format_cli_output(result)
