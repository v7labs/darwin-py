import re
import tempfile
import uuid
from pathlib import Path
from subprocess import run
from typing import Generator, Optional, Tuple

import pytest

from darwin.exceptions import DarwinException
from e2e_tests.objects import E2EDataset
from e2e_tests.setup_tests import create_random_image


def run_cli_command(command: str, working_directory: Optional[str] = None) -> Tuple[int, str, str]:
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

    return result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8")
