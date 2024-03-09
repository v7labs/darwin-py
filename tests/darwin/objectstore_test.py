from pathlib import Path

import pytest

from darwin.client import Client
from darwin.config import Config
from darwin.dataset.remote_dataset_v2 import RemoteDatasetV2
from darwin.objectstore import ObjectStore


class TestObjectStore:
    @pytest.fixture
    def object_store(self):
        return ObjectStore(
            name="test",
            prefix="test_prefix",
            readonly=False,
            provider="aws",
            default=True,
        )

    @pytest.fixture
    def darwin_client(
        darwin_config_path: Path,
        darwin_datasets_path: Path,
        team_slug_darwin_json_v2: str,
    ) -> Client:
        config = Config(darwin_config_path)
        config.put(["global", "api_endpoint"], "http://localhost/api")
        config.put(["global", "base_url"], "http://localhost")
        config.put(["teams", team_slug_darwin_json_v2, "api_key"], "mock_api_key")
        config.put(
            ["teams", team_slug_darwin_json_v2, "datasets_dir"],
            str(darwin_datasets_path),
        )
        return Client(config)

    @pytest.fixture
    def remote_dataset_v2(self):
        return RemoteDatasetV2(
            client=self.darwin_client,
            team="test_team",
            name="Test dataset",
            slug="test-dataset",
            dataset_id=1,
        )

    def test_init(self, object_store):
        assert object_store.name == "test"
        assert object_store.prefix == "test_prefix"
        assert object_store.readonly is False
        assert object_store.provider == "aws"
        assert object_store.default is True

    def test_str(self, object_store):
        assert (
            str(object_store)
            == "A read-write aws storage connection named test with prefix: test_prefix"
        )

    def test_repr(self, object_store):
        assert (
            repr(object_store)
            == "ObjectStore(name=test, prefix=test_prefix, readonly=False, provider=aws)"
        )
