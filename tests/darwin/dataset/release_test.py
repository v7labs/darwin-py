import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from darwin.dataset.release import Release, ReleaseStatus
from tests.fixtures import *


@pytest.fixture
def release(dataset_slug: str, team_slug_darwin_json_v2: str) -> Release:
    return Release(
        dataset_slug=dataset_slug,
        team_slug=team_slug_darwin_json_v2,
        version="latest",
        name="test",
        status=ReleaseStatus("pending"),
        url="http://test.v7labs.com/",
        export_date=datetime.fromisoformat("2021-01-01T00:00:00+00:00"),
        image_count=None,
        class_count=None,
        available=True,
        latest=True,
        format="darwin",
    )


class TestRelease:
    def test_downloads_zip(self, release: Release, tmp_path: Path):
        with patch.object(requests, "get") as get:
            with patch.object(shutil, "copyfileobj") as copyfileobj:
                release.download_zip(tmp_path / "test.zip")
                get.assert_called_once_with("http://test.v7labs.com/", stream=True)
                copyfileobj.assert_called_once()
