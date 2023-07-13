from os import environ
from os.path import dirname, join
from pathlib import Path
from typing import Optional, Tuple

import dotenv
import pytest


def pytest_configure(_: pytest.Config) -> None:
    ...


def pytest_sessionstart(session: pytest.Session) -> None:
    dotenv_file_location: Path = Path(join(dirname(__file__), "../.env")).absolute()

    if not dotenv_file_location.exists():
        raise FileNotFoundError(f"Could not find .env file at {dotenv_file_location}")

    dotenv.load_dotenv(dotenv_file_location)

    server = environ.get("E2E_ENVIRONMENT")
    api_key = environ.get("E2E_API_KEY")

    if server is None:
        raise ValueError("E2E_ENVIRONMENT is not set")

    if api_key is None:
        raise ValueError("E2E_API_KEY is not set")

    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    session.config.cache.set("server", server)
    session.config.cache.set("api_key", api_key)


@pytest.fixture(
    scope="session", autouse=True
)  # autouse=True means that this fixture will be automatically used by all tests
def config_values(session: pytest.Session) -> Tuple[str, str]:
    if not isinstance(session.config.cache, pytest.Cache):
        raise TypeError("Pytest caching is not enabled, but E2E tests require it")

    server = session.config.cache.get("server", None)
    api_key = session.config.cache.get("api_key", None)

    if server is None:
        raise ValueError("E2E_ENVIRONMENT is not set")

    if api_key is None:
        raise ValueError("E2E_API_KEY is not set")

    return server, api_key
