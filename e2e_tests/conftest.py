from os import environ
from os.path import dirname, join
from pathlib import Path
from time import sleep
from typing import List

import dotenv
import pytest

from darwin.future.data_objects.typing import UnknownType
from e2e_tests.exceptions import E2EEnvironmentVariableNotSet
from e2e_tests.objects import ConfigValues, E2EDataset
from e2e_tests.setup_tests import setup_tests, teardown_tests


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("addopts", "--ignore=../tests/, ../future --capture=tee-sys")


def pytest_sessionstart(session: pytest.Session) -> None:
    # Use dotenv values _if_ present
    dotenv_file_location: Path = Path(join(dirname(__file__), ".env")).resolve()
    if dotenv_file_location.exists():
        dotenv.load_dotenv(dotenv_file_location)

    server = environ.get("E2E_ENVIRONMENT")
    api_key = environ.get("E2E_API_KEY")
    team_slug = environ.get("E2E_TEAM")

    if server is None:
        raise E2EEnvironmentVariableNotSet("E2E_ENVIRONMENT")

    if api_key is None:
        raise E2EEnvironmentVariableNotSet("E2E_API_KEY")

    if team_slug is None:
        raise E2EEnvironmentVariableNotSet("E2E_TEAM")

    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    session.config.cache.set("server", server)
    session.config.cache.set("api_key", api_key)
    session.config.cache.set("team_slug", team_slug)

    datasets = setup_tests(ConfigValues(server=server, api_key=api_key, team_slug=team_slug))
    # pytest.datasets = datasets
    setattr(pytest, "datasets", datasets)
    # Set the environment variables for running CLI arguments
    environ["DARWIN_BASE_URL"] = server
    environ["DARWIN_TEAM"] = team_slug
    environ["DARWIN_API_KEY"] = api_key

    print("Sleeping for 10 seconds to allow the server to catch up")
    sleep(10)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    datasets = pytest.datasets
    if datasets is None:
        raise ValueError("Datasets were not created, so could not tear them down")

    server = session.config.cache.get("server", None)
    api_key = session.config.cache.get("api_key", None)
    team = session.config.cache.get("team_slug", None)

    if server is None or api_key is None or team is None:
        raise ValueError("E2E environment variables were not cached")

    del environ["DARWIN_BASE_URL"]
    del environ["DARWIN_TEAM"]
    del environ["DARWIN_API_KEY"]

    config = ConfigValues(server=server, api_key=api_key, team_slug=team)
    assert isinstance(datasets, List)
    teardown_tests(config, datasets)


@pytest.fixture(
    scope="session", autouse=True
)  # autouse=True means that this fixture will be automatically used by all tests
def config_values(request: UnknownType) -> ConfigValues:
    session = request.node.session

    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    server = session.config.cache.get("server", None)
    api_key = session.config.cache.get("api_key", None)
    team = session.config.cache.get("team_slug", None)

    if server is None:
        raise ValueError("E2E_ENVIRONMENT is not set")

    if api_key is None:
        raise ValueError("E2E_API_KEY is not set")

    if team is None:
        raise ValueError("E2E_TEAM is not set")

    return ConfigValues(server=server, api_key=api_key, team_slug=team)
