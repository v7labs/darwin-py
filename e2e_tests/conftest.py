from collections import namedtuple
from os import environ
from os.path import dirname, join
from pathlib import Path
from pprint import pprint

import dotenv
import pytest

from e2e_tests.exceptions import E2EEnvironmentVariableNotSet


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("addopts", "--ignore=../tests/, ../future")


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

    session.config.cache.set("server", server)
    session.config.cache.set("api_key", api_key)


ConfigValues = namedtuple("ConfigValues", ["server", "api_key"])


@pytest.fixture(
    scope="session", autouse=True
)  # autouse=True means that this fixture will be automatically used by all tests
def config_values(request) -> ConfigValues:
    pprint(request)
    session = request.node.session

    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    server = session.config.cache.get("server", None)
    api_key = session.config.cache.get("api_key", None)

    if server is None:
        raise ValueError("E2E_ENVIRONMENT is not set")

    if api_key is None:
        raise ValueError("E2E_API_KEY is not set")

    return ConfigValues(server=server, api_key=api_key)
