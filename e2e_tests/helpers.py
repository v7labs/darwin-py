from subprocess import run
from typing import Optional, Tuple

from darwin.exceptions import DarwinException
from e2e_tests.objects import E2EDataset


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


def create_local_dataset(working_directory: str, dataset_name: str) -> Tuple[int, str, str]:
    """
    Create a local dataset.

    Parameters
    ----------
    working_directory : str
        The working directory to create the dataset in.
    dataset_name : str
        The name of the dataset to create.
    """

    return run_cli_command(f"darwin dataset create {dataset_name}", working_directory)
