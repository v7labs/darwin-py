import unittest
from urllib.parse import urlparse

import pytest
import responses
from pydantic import ValidationError
from requests import HTTPError

from darwin.future.core.client import Client, Config
from darwin.future.exceptions.base import DarwinException
from darwin.future.exceptions.client import NotFound, Unauthorized


@pytest.fixture
def base_config() -> Config:
    return Config(api_key="test_key", base_url="http://test_url.com/", default_team=None)


@pytest.fixture
def base_client(base_config: Config) -> Client:
    return Client(base_config)


def test_create_config(base_config: Config) -> None:
    assert base_config.api_key == "test_key"
    assert base_config.base_url == "http://test_url.com/"
    assert base_config.default_team is None


def test_config_base_url(base_config: Config) -> None:
    assert base_config.base_url == "http://test_url.com/"

    # Test that the base_url validates after being created
    base_config.base_url = "https://test_url.com"
    assert base_config.base_url == "https://test_url.com/"

    # Test that the base_url fails validation on invalid url strings
    with pytest.raises(ValidationError):
        base_config.base_url = "test_url.com"
        base_config.base_url = "ftp://test_url.com"
        base_config.base_url = ""


def test_client(base_client: Client) -> None:
    assert base_client.config.api_key == "test_key"
    assert base_client.config.base_url == "http://test_url.com/"
    assert base_client.config.default_team is None

    assert base_client.session is not None
    assert base_client.headers is not None
    assert base_client.headers == {"Content-Type": "application/json", "Authorization": "ApiKey test_key"}

    # Test client functionality works
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://test_url.com/test_endpoint", json={"test": "test"}, status=200)
        rsps.add(responses.PUT, "http://test_url.com/test_endpoint", json={"test": "test"}, status=200)
        rsps.add(responses.POST, "http://test_url.com/test_endpoint", json={"test": "test"}, status=200)
        rsps.add(responses.DELETE, "http://test_url.com/test_endpoint", json={"test": "test"}, status=200)
        rsps.add(responses.PATCH, "http://test_url.com/test_endpoint", json={"test": "test"}, status=200)

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
def test_client_raises_darwin(status_code: int, exception: DarwinException, base_client: Client) -> None:
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.get("test_endpoint")
        rsps.reset()
        rsps.add(responses.PUT, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.put("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.POST, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.post("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.DELETE, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.delete("test_endpoint")
        rsps.reset()
        rsps.add(responses.PATCH, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(exception):  # type: ignore
            base_client.patch("test_endpoint", {"test": "test"})


def test_client_raises_generic(base_client: Client) -> None:
    status_code = 499
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.get("test_endpoint")
        rsps.reset()
        rsps.add(responses.PUT, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.put("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.POST, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.post("test_endpoint", {"test": "test"})
        rsps.reset()
        rsps.add(responses.DELETE, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.delete("test_endpoint")
        rsps.reset()
        rsps.add(responses.PATCH, "http://test_url.com/test_endpoint", json={"test": "test"}, status=status_code)
        with pytest.raises(HTTPError):
            base_client.patch("test_endpoint", {"test": "test"})
