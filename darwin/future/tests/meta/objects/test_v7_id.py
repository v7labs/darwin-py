from uuid import UUID

from darwin.future.meta.client import Client
from darwin.future.meta.objects.v7_id import V7ID
from darwin.future.tests.meta.fixtures import *


def test_v7_id(base_meta_client: Client) -> None:
    # Test creating a V7ID object
    uuid = UUID("123e4567-e89b-12d3-a456-426655440000")
    v7_id = V7ID(uuid, base_meta_client)
    assert v7_id.id == uuid

    # Test __str__ method
    assert str(v7_id) == str(uuid)

    # Test __repr__ method
    assert repr(v7_id) == str(uuid)
