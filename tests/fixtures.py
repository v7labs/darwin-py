import shutil
from pathlib import Path

import pytest

from darwin.config import Config


@pytest.fixture
def darwin_path(tmp_path: Path) -> Path:
    return tmp_path / "darwin-test"


@pytest.fixture
def darwin_config_path(darwin_path: Path) -> Path:
    return darwin_path / "config.yaml"


@pytest.fixture
def darwin_datasets_path(darwin_path: Path) -> Path:
    return darwin_path / "datasets"


@pytest.fixture
def team_slug() -> str:
    return "v7"


@pytest.fixture
def dataset_name() -> str:
    return "test_dataset"


@pytest.fixture
def dataset_slug() -> str:
    return "test-dataset"


@pytest.fixture
def release_name() -> str:
    return "latest"


@pytest.fixture
def file_read_write_test(darwin_path: Path, team_slug: str, dataset_name: str):
    # Executed before the test
    dataset_path = darwin_path / "datasets" / team_slug / dataset_name
    dataset_path.mkdir(parents=True)

    # Useful if the test needs to reuse attrs
    yield

    # Executed after the test
    shutil.rmtree(darwin_path)


@pytest.fixture
def local_config_file(team_slug: str):
    config_path = Path.home() / ".darwin" / "config.yaml"
    backup_config_path = Path.home() / ".darwin" / "config.yaml.bak"

    # Executed before the test
    if config_path.exists():
        shutil.move(config_path, backup_config_path)
        config = Config(config_path)

    config = Config(config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug, "api_key"], "mock_api_key")

    # Useful if the test needs to reuse attrs
    yield config

    # Executed after the test
    config_path.unlink()
    if backup_config_path.exists():
        shutil.move(backup_config_path, config_path)
