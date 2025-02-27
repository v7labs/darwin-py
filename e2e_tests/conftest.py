from os import environ
from os.path import dirname, join
from pathlib import Path
from time import sleep
from typing import List, Generator

import dotenv
import pytest
import tempfile

from darwin.future.data_objects.typing import UnknownType
from e2e_tests.exceptions import E2EEnvironmentVariableNotSet
from e2e_tests.objects import ConfigValues, E2EDataset
from e2e_tests.helpers import new_dataset  # noqa: F401
from e2e_tests.setup_tests import (
    setup_annotation_classes,
    setup_datasets,
    teardown_annotation_classes,
    setup_item_level_properties,
    teardown_item_level_properties,
    teardown_tests,
    generate_random_string,
)


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

    config = ConfigValues(server=server, api_key=api_key, team_slug=team_slug)

    run_prefix = f"test_{generate_random_string(6)}"

    datasets = setup_datasets(config)
    # Ensure that there are no annotation classes or item-level properties before running tests
    teardown_annotation_classes(config, [], run_prefix=run_prefix)
    teardown_item_level_properties(config, [], run_prefix=run_prefix)
    annotation_classes = setup_annotation_classes(config, run_prefix=run_prefix)
    item_level_properties = setup_item_level_properties(config, run_prefix=run_prefix)

    # pytest.datasets = datasets
    setattr(pytest, "datasets", datasets)
    setattr(pytest, "annotation_classes", annotation_classes)
    setattr(pytest, "item_level_properties", item_level_properties)
    setattr(pytest, "config_values", config)
    setattr(pytest, "run_prefix", run_prefix)

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
    annotation_classes = pytest.annotation_classes
    if annotation_classes is None:
        raise ValueError(
            "Annotation classes were not created, so could not tear them down"
        )
    item_level_properties = pytest.item_level_properties
    if item_level_properties is None:
        raise ValueError(
            "Item-level properties were not created, so could not tear them down"
        )
    run_prefix = getattr(pytest, "run_prefix", None)
    if run_prefix is None:
        print("Warning: No run prefix found, teardown may affect other test runs")

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
    assert isinstance(annotation_classes, List)
    teardown_annotation_classes(config, annotation_classes, run_prefix=run_prefix)
    assert isinstance(item_level_properties, List)
    teardown_item_level_properties(config, item_level_properties, run_prefix=run_prefix)


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


@pytest.fixture
def local_dataset(
    new_dataset: E2EDataset,  # noqa: F811
) -> Generator[E2EDataset, None, None]:
    with tempfile.TemporaryDirectory() as temp_directory:
        new_dataset.directory = temp_directory
        yield new_dataset
