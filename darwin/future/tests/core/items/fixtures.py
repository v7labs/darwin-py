from typing import List
from uuid import UUID, uuid4

import pytest


@pytest.fixture
def UUIDs() -> List[UUID]:
    return [uuid4() for i in range(10)]

@pytest.fixture
def UUIDs_str(UUIDs: List[UUID]) -> List[str]:
    return [str(uuid) for uuid in UUIDs]

@pytest.fixture
def stage_id() -> UUID:
    return uuid4()

@pytest.fixture
def workflow_id() -> UUID:
    return uuid4()