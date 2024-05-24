from pathlib import Path

import pytest
import responses
from pydantic import ValidationError
from requests import HTTPError

from darwin.config import Config as OldConfig
from darwin.future.core.client import ClientCore, DarwinConfig, TeamsConfig
from darwin.future.exceptions import DarwinException, NotFound, Unauthorized
from darwin.future.tests.core.fixtures import *
from darwin.future.tests.fixtures import *
from tests.fixtures import *


def test_create_config(base_config: DarwinConfig) -> None:
    assert base_config.api_key == "test_key"
    assert base_config.base_url == "http://test_url.com/"
    assert base_config.default_team == "default-team"


def test_config_base_url(base_config: DarwinConfig) -> None:
    assert base_config.base_url == "http://test_url.com/"

    # Test that the base_url validates after being created
    base_config.base_url = "https://test_url.com"
    assert base_config.base_url == "https://test_url.com/"

    # Test that the base_url fails validation on invalid url strings
    with pytest.raises(ValidationError):
        base_config.base_url = "test_url.com"
        base_config.base_url = "ftp://test_url.com"
        base_config.base_url = ""


@pytest.mark.parametrize("base_url", ["test_url.com", "ftp://test_url.com", ""])
def test_invalid_config_url_validation(base_url: str, tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        DarwinConfig(
            api_key="test_key",
            datasets_dir=tmp_path,
            api_endpoint="http://test_url.com/api/",
            base_url=base_url,
            default_team="default-team",
            teams={},
        )


def test_client(base_client: ClientCore) -> None:
    assert base_client.config.api_key == "test_key"
    assert base_client.config.base_url == "http://test_url.com/"
    assert base_client.config.default_team == "default-team"

    assert base_client.session is not None
    assert base_client.headers is not None
    assert base_client.headers == {
        "Content-Type": "application/json",
        "Authorization": "ApiKey test_key",
        "Accept": "application/json",
    }

    # Test client functionality works
    endpoint = base_client.config.api_endpoint + "test_endpoint"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json={"test": "test"}, status=200)
        rsps.add(responses.PUT, endpoint, json={"test": "test"}, status=200)
        rsps.add(responses.POST, endpoint, json={"test": "test"}, status=200)
        rsps.add(responses.DELETE, endpoint, json={"test": "test"}, status=200)
        rsps.add(responses.PATCH, endpoint, json={"test": "test"}, status=200)

        # Test get
        response = base_client.get("test_endpoint")
        assert response == {"test": "test"}

        # Test put
        response = base_client.put("test_endpoint", {"test": "test"})
        assert response == {"test": "test"}

        # Test post
        response = base_client.post("test_endpoint", {"test": "test"})
        assert response == {"test": "test"}

        # Test delete
        response = base_client.delete("test_endpoint")
        assert response == {"test": "test"}

        # Test patch
        response = base_client.patch("test_endpoint", {"test": "test"})
        assert response == {"test": "test"}


@pytest.mark.parametrize(
    "status_code, exception",
    [(401, Unauthorized), (404, NotFound)],
)
def test_client_raises_darwin(
    status_code: int, exception: DarwinException, base_client: ClientCore
) -> None:
    endpoint = base_client.config.api_endpoint + "test_endpoint"
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.get("test_endpoint")
        rsps.reset()
        rsps.add(responses.PUT, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.put("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.POST, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.post("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.DELETE, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.delete("test_endpoint")
        rsps.reset()
        rsps.add(responses.PATCH, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.patch("test_endpoint", {"test": "test"})


def test_client_raises_generic(base_client: ClientCore) -> None:
    endpoint = base_client.config.api_endpoint + "test_endpoint"
    status_code = 499
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.get("test_endpoint")
        rsps.reset()
        rsps.add(responses.PUT, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.put("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.POST, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.post("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.DELETE, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.delete("test_endpoint")
        rsps.reset()
        rsps.add(responses.PATCH, endpoint, json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.patch("test_endpoint", {"test": "test"})


@pytest.mark.usefixtures("file_read_write_test")
def test_config_from_old_error(
    base_config: DarwinConfig, darwin_config_path: Path
) -> None:
    old_config = OldConfig(darwin_config_path)
    team_slug = "test-team"
    with pytest.raises(ValueError) as excinfo:
        base_config.from_old(old_config, team_slug)
    (msg,) = excinfo.value.args
    assert msg == "No teams found in the old config"


@pytest.mark.usefixtures("file_read_write_test")
def test_config_from_old(
    base_config: DarwinConfig, darwin_config_path: Path, darwin_datasets_path: Path
) -> None:
    old_config = OldConfig(darwin_config_path)
    team_slug = "test-team"
    old_config.put(["global", "api_endpoint"], "http://localhost/api")
    old_config.put(["global", "base_url"], "http://localhost")
    old_config.put(["teams", team_slug, "api_key"], "mock_api_key")
    old_config.put(["teams", team_slug, "datasets_dir"], str(darwin_datasets_path))
    darwin_config = base_config.from_old(old_config, team_slug)

    assert darwin_config.api_key == "mock_api_key"
    assert darwin_config.base_url == "http://localhost/"
    assert darwin_config.api_endpoint == "http://localhost/api"
    assert darwin_config.default_team == team_slug
    assert darwin_config.teams == {
        team_slug: TeamsConfig(
            api_key="mock_api_key", datasets_dir=darwin_datasets_path
        )
    }
