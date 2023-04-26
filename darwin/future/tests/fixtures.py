import os
import shutil
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def test_directory() -> Generator[Path, None, None]:
    path = Path.home() / "darwin-tests"
    if not path.exists():
        os.makedirs(path)
    yield path
    shutil.rmtree(path)
