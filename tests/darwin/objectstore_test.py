import pytest

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
