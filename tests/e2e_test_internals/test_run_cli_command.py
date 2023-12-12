from collections import namedtuple
from unittest import mock

import pytest

from darwin.exceptions import DarwinException
from e2e_tests.helpers import run_cli_command


def test_does_not_allow_directory_traversal() -> None:
    with pytest.raises(DarwinException) as excinfo:
        run_cli_command("darwin --help; ls ..", server_wait=0)

        assert excinfo.value == "Cannot pass directory traversal to 'run_cli_command'."

    with pytest.raises(DarwinException) as excinfo:
        run_cli_command(
            "darwin --help", working_directory="/usr/bin/../", server_wait=0
        )
        assert excinfo.value == "Cannot pass directory traversal to 'run_cli_command'."


@mock.patch("e2e_tests.helpers.run")
def test_passes_working_directory_to_run_cli_command(
    mock_subprocess_run: mock.Mock,
) -> None:
    mock_subprocess_run.reset_mock()
    run_cli_command("darwin --help", "/usr/bin", server_wait=0)

    mock_subprocess_run.assert_called_once()
    assert mock_subprocess_run.call_args[0][0] == "darwin --help"
    assert mock_subprocess_run.call_args[1]["cwd"] == "/usr/bin"


@mock.patch("e2e_tests.helpers.run")
def test_passes_back_returncode_stdout_and_stderr(
    mock_subprocess_run: mock.Mock,
) -> None:
    CompletedProcess = namedtuple(
        "CompletedProcess", ["returncode", "stdout", "stderr"]
    )
    mocked_output = CompletedProcess(returncode=137, stdout=b"stdout", stderr=b"stderr")

    mock_subprocess_run.return_value = mocked_output

    result = run_cli_command("darwin --help", "/usr/bin", server_wait=0)

    mock_subprocess_run.assert_called_once()

    assert result.return_code == 137
    assert result.stdout == "stdout"
    assert result.stderr == "stderr"


@mock.patch("e2e_tests.helpers.run")
def test_does_not_pass_working_directory_to_run_cli_command(
    mock_subprocess_run: mock.Mock,
) -> None:
    mock_subprocess_run.reset_mock()
    run_cli_command("darwin --help", server_wait=0)

    mock_subprocess_run.assert_called_once()
    assert mock_subprocess_run.call_args[0][0] == "darwin --help"
    assert "cwd" not in mock_subprocess_run.call_args[1]


if __name__ == "__main__":
    pytest.main()
