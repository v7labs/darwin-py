import tempfile
from os import environ
from os.path import dirname, join
from pathlib import Path
from time import sleep
from typing import Generator, List, Tuple

import dotenv
import pytest

from darwin.future.data_objects.typing import UnknownType
from e2e_tests.exceptions import E2EEnvironmentVariableNotSet
from e2e_tests.fixtures.team_management import (
    create_isolated_team,
    delete_isolated_team,
)
from e2e_tests.helpers import assert_cli, new_dataset, run_cli_command  # noqa: F401
from e2e_tests.logger_config import logger
from e2e_tests.objects import ConfigValues, E2EDataset, TeamConfigValues


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "addopts", "--ignore=../tests/, ../future --capture=tee-sys"
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    # Use dotenv values _if_ present
    dotenv_file_location: Path = Path(join(dirname(__file__), ".env")).resolve()
    if dotenv_file_location.exists():
        dotenv.load_dotenv(dotenv_file_location)

    server = environ.get("E2E_ENVIRONMENT")
    api_key = environ.get("E2E_API_KEY")

    if server is None:
        raise E2EEnvironmentVariableNotSet("E2E_ENVIRONMENT")

    if api_key is None:
        raise E2EEnvironmentVariableNotSet("E2E_API_KEY")

    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    session.config.cache.set("server", server)  # TODO needed?
    session.config.cache.set("superadmin_api_key", api_key)

    # Create base config without team_slug
    config = ConfigValues(server=server, superadmin_api_key=api_key)

    # Store the base config for tests to use
    setattr(pytest, "config_values", config)

    # Set the environment variables for running CLI arguments
    environ["DARWIN_BASE_URL"] = server


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    # Clean up environment variables
    if "DARWIN_BASE_URL" in environ:
        del environ["DARWIN_BASE_URL"]


@pytest.fixture(
    scope="session", autouse=True
)  # autouse=True means that this fixture will be automatically used by all tests
def config_values(request: UnknownType) -> ConfigValues:
    session = request.node.session

    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    server = session.config.cache.get("server", None)
    api_key = session.config.cache.get("superadmin_api_key", None)

    if server is None:
        raise ValueError("E2E_ENVIRONMENT is not set")

    if api_key is None:
        raise ValueError("E2E_API_KEY is not set")

    return ConfigValues(server=server, superadmin_api_key=api_key)


@pytest.fixture
def local_dataset(
    new_dataset: E2EDataset,  # noqa: F811
) -> Generator[E2EDataset, None, None]:
    with tempfile.TemporaryDirectory() as temp_directory:
        new_dataset.directory = temp_directory
        yield new_dataset


@pytest.fixture
def isolated_team(
    request: pytest.FixtureRequest, config_values: ConfigValues
) -> Generator[TeamConfigValues, None, None]:
    """
    Create an isolated team for a test and clean it up afterward

    Returns
    -------
    Generator[TeamConfigValues, None, None]
        Team configuration for the isolated team
    """
    team_data = None

    try:
        team_data = create_isolated_team(config_values)

        # Create a temporary directory for darwin datasets

        logger.info("Authenticating team in darwinpy")
        result = run_cli_command(
            f"yes N | darwin authenticate --api_key {team_data['api_key']} --datasets_dir ~/.darwin/datasets"
        )  # do not make team default
        assert_cli(result, 0)

        # Create a team config with the isolated team details
        team_config = TeamConfigValues(
            api_key=team_data["api_key"],
            team_slug=team_data["slug"],
            team_id=team_data["id"],
        )

        def cleanup():
            """Ensure team is deleted even if test fails"""
            if team_data:
                try:
                    delete_isolated_team(team_config, config_values)
                except Exception as e:
                    logger.warning(
                        f"Warning: Failed to cleanup team {team_config.team_id}: {str(e)}"
                    )

        # Register the cleanup function to run even if test fails
        request.addfinalizer(cleanup)

        yield team_config

    except Exception as e:
        # If team creation fails, ensure we try to clean up if team was partially created
        if team_data:
            try:
                delete_isolated_team(team_config, config_values)
            except:
                pass  # Already in an error state, just continue with original error
        raise  # Re-raise the original exception
