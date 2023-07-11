from unittest import mock

import pytest

from darwin.exceptions import DarwinException
from e2e_tests import run_cli_command


def test_does_not_allow_directory_traversal() -> None:
    with pytest.raises(DarwinException) as excinfo:
        run_cli_command("darwin --help; ls ..")

        assert excinfo.value == "Cannot pass directory traversal to 'run_cli_command'."

    with pytest.raises(DarwinException) as excinfo:
        run_cli_command("darwin --help", working_directory="/usr/bin/../")
        assert excinfo.value == "Cannot pass directory traversal to 'run_cli_command'."


@mock.patch("")
def test_passes_working_directory_to_run_cli_command(mock_subprocess_run: mock.Mock) -> None:
    mock_subprocess_run.reset_mock()
    run_cli_command("darwin --help", working_directory="/usr/bin")
    mock_subprocess_run.assert_called_with("darwin --help", working_directory="/usr/bin")


@mock.patch("")
def test_does_not_pass_working_directory_to_run_cli_command(mock_subprocess_run: mock.Mock) -> None:
    mock_subprocess_run.reset_mock()
    run_cli_command("darwin --help")
    mock_subprocess_run.assert_called_with("darwin --help")


if __name__ == "__main__":
    pytest.main()
