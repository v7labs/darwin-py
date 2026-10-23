import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from darwin.dataset.release import Release, ReleaseStatus
from tests.fixtures import *
from tests.darwin.dataset.remote_dataset_test import darwin_client


@pytest.mark.usefixtures("file_read_write_test")
def test_pretty_pull_preserves_tokens_after_actual_media_download(remote_dataset):
    with zipfile.ZipFile("tests/dataset_with_properties.zip") as archive:
        original = archive.read("ferrari-laferrari.json")
    original = original.rstrip()[:-1] + (
        b',"precision":[1.0000,1e+002,-0,0.12345678901234567890123456789],'
        b'"escaped":"\\u0061\\/"}'
    )
    release = Release(
        remote_dataset.slug,
        remote_dataset.team,
        "0.1.0",
        "pretty-print-media-test",
        ReleaseStatus("complete"),
        "http://darwin-fake-url.com",
        datetime.now(),
        None,
        None,
        False,
        True,
        "darwin_json_2",
    )

    def download_zip(path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("image.json", original)
        return path

    response = MagicMock(
        ok=True, status_code=200, headers={"Content-Type": "image/jpeg"}
    )
    response.__iter__.return_value = [b"media bytes"]
    with (
        patch.object(Release, "download_zip", side_effect=download_zip),
        patch.object(
            remote_dataset.client, "_get_raw_from_full_url", return_value=response
        ),
    ):
        _, count = remote_dataset.pull(
            release=release, pretty_print=True, multi_processed=False
        )
    assert count == 1
    output = next(
        (remote_dataset.local_releases_path / release.name / "annotations").glob(
            "*.json"
        )
    )
    formatted = output.read_bytes()
    assert (
        re.search(rb'"precision":\s*(\[[^\]]+\])', formatted)
        .group(1)
        .replace(b"\n", b"")
        .replace(b" ", b"")
        == b"[1.0000,1e+002,-0,0.12345678901234567890123456789]"
    )
    assert b'"\\u0061\\/"' in formatted
    parsed = json.loads(formatted)
    local_path = Path(parsed["item"]["slots"][0]["source_files"][0]["local_path"])
    assert local_path.read_bytes() == b"media bytes"
