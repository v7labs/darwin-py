import unittest

import pytest
import responses

from darwin.future.core.client import DarwinConfig
from darwin.future.meta.client import MetaClient


def test_creates_from_api_key() -> None:
    with responses.RequestsMock() as rsps:
        base_api_endpoint = DarwinConfig._default_api_endpoint()
        rsps.add(responses.GET, base_api_endpoint + "users/token_info", json={"selected_team": {"slug": "test-team"}})
        client = MetaClient.from_api_key(api_key="test")
        assert client.config.default_team == "test-team"
