import json
from dataclasses import dataclass
import re
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from darwin.dataset.release import Release, ReleaseStatus
from darwin.dataset.download_manager import download_all_images_from_annotations
from darwin.dataset.json_formatter import PrettyPrintError
from darwin.dataset.utils import exhaust_generator
from tests.fixtures import *
from tests.darwin.dataset.remote_dataset_test import darwin_client as darwin_client


@pytest.mark.usefixtures("file_read_write_test")
@pytest.mark.parametrize("blocking", [True, False])
def test_pretty_pull_preserves_tokens_after_actual_media_download(
    remote_dataset, blocking
):
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
        progress, count = remote_dataset.pull(
            release=release, pretty_print=True, multi_processed=False, blocking=blocking
        )
        if not blocking:
            for task in progress():
                task()
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
    local_path = Path(parsed["item"]["slots"][0]["source_files"][0].pop("local_path"))
    assert local_path.read_bytes() == b"media bytes"
    assert parsed == json.loads(original)


@dataclass
class _MediaResponse:
    ok: bool = True
    headers = {"Content-Type": "image/jpeg"}

    def __iter__(self):
        yield b"media bytes"


@dataclass
class _MediaClient:
    failed_urls: tuple[str, ...] = ()

    def _get_raw_from_full_url(self, url, stream=True):
        if url in self.failed_urls:
            raise OSError(f"download failed {url}")
        return _MediaResponse()


def _media_annotation(tmp_path, kind="multi", repeated_url=False):
    annotations = tmp_path / "annotations"
    annotations.mkdir()
    slots = [
        {
            "slot_name": name,
            "type": "video" if kind == "video" else "image",
            "source_files": [
                {
                    "local_path": "old path",
                    "file_name": "z.dcm",
                    "url": f"http://media/{name}/z",
                },
                {
                    "file_name": "a.dcm",
                    "url": f"http://media/{name}/a",
                    "local_path": "another old path",
                },
                {"file_name": "m.dcm", "url": f"http://media/{name}/m"},
            ],
        }
        for name in (["z", "a"] if kind == "multi" else ["z"])
    ]
    if kind != "multi":
        slots[0]["source_files"] = slots[0]["source_files"][:1]
        slots[0]["source_files"][0]["file_name"] = (
            "z.mp4" if kind == "video" else "z.jpg"
        )
    if repeated_url:
        for slot in slots:
            for source in slot["source_files"]:
                source["url"] = "http://media/shared"
    data = {
        "version": "2.0",
        "schema_ref": "schema",
        "item": {
            "name": "item.mp4" if kind == "video" else "item.jpg",
            "path": "/nested",
            "slots": slots,
        },
        "annotations": [],
        "properties": [{"name": "test", "value": "unchanged"}],
        "authors": [{"name": "Author", "id": "001"}],
    }
    raw = json.dumps(data).encode().rstrip()[:-1] + (
        b',"precision":[1.0000,1e+002,-0,0.12345678901234567890123456789],'
        b'"escaped":"\\u0061\\/"}'
    )
    raw = (
        raw.replace(b'"item":', b'"it\\u0065m":')
        .replace(b'"source_files":', b'"source_\\u0066iles":')
        .replace(b'"local_path":', b'"local_\\u0070ath":')
    )
    path = annotations / "annotation.json"
    path.write_bytes(raw)
    return path, tmp_path / "images"


@pytest.mark.parametrize("kind", ["image", "video", "multi"])
@pytest.mark.parametrize("multi_processed", [False, True])
def test_media_callbacks_preserve_unsorted_source_tokens(
    tmp_path, kind, multi_processed
):
    path, images = _media_annotation(tmp_path, kind)
    original = path.read_bytes()
    progress, count = download_all_images_from_annotations(
        _MediaClient(), path.parent, images, pretty_print=True
    )
    tasks = progress()
    assert count == (6 if kind == "multi" else 1)
    assert len(tasks) == 1
    successes, errors = exhaust_generator(
        tasks, len(tasks), multi_processed=multi_processed, worker_count=2
    )
    assert errors == []
    assert len(successes) == 1
    output = path.read_bytes()
    assert b"1.0000" in output
    assert b"1e+002" in output
    assert b"-0," in output
    assert b"0.12345678901234567890123456789" in output
    assert b'"\\u0061\\/"' in output
    assert b'"it\\u0065m"' in output
    assert b'"source_\\u0066iles"' in output
    assert b'"local_\\u0070ath"' in output
    expected = json.loads(original)
    actual = json.loads(output)
    for slot in actual["item"]["slots"]:
        for source in slot["source_files"]:
            local_path = Path(source.pop("local_path"))
            if kind == "multi":
                assert local_path.parent.name == slot["slot_name"]
                assert local_path.name == source["file_name"]
            else:
                assert local_path.name == (
                    "item.mp4" if kind == "video" else "item.jpg"
                )
            assert local_path.read_bytes() == b"media bytes"
    for slot in expected["item"]["slots"]:
        for source in slot["source_files"]:
            source.pop("local_path", None)
    assert actual == expected
    assert not list(path.parent.glob("*.tmp"))


def test_repeated_urls_retain_legacy_last_successful_path_semantics(tmp_path):
    path, images = _media_annotation(tmp_path, repeated_url=True)
    progress, count = download_all_images_from_annotations(
        _MediaClient(), path.parent, images, pretty_print=True
    )
    for task in progress():
        task()
    assert count == 6
    slots = json.loads(path.read_bytes())["item"]["slots"]
    local_paths = {
        source["local_path"] for slot in slots for source in slot["source_files"]
    }
    assert local_paths == {str(images / "nested/item.jpg/z/m.dcm")}
    assert b"1.0000" in path.read_bytes()


def test_download_failure_still_records_other_successful_local_paths(tmp_path):
    path, images = _media_annotation(tmp_path)
    progress, count = download_all_images_from_annotations(
        _MediaClient(("http://media/z/a",)), path.parent, images, pretty_print=True
    )
    tasks = progress()
    successes, errors = exhaust_generator(tasks, len(tasks), multi_processed=False)
    assert successes == []
    assert len(errors) == 1
    assert str(errors[0]) == "download failed http://media/z/a"
    assert count == 6
    sources = json.loads(path.read_bytes())["item"]["slots"][0]["source_files"]
    assert Path(sources[0]["local_path"]).read_bytes() == b"media bytes"
    assert sources[1]["local_path"] == "another old path"
    assert Path(sources[2]["local_path"]).read_bytes() == b"media bytes"
    assert b"1.0000" in path.read_bytes()


def test_failed_trace_edit_retains_annotation_bytes(tmp_path):
    path, images = _media_annotation(tmp_path)
    original = path.read_bytes()
    progress, _ = download_all_images_from_annotations(
        _MediaClient(), path.parent, images, pretty_print=True
    )
    with patch(
        "darwin.dataset.json_formatter.os.replace", side_effect=OSError("disk full")
    ):
        with pytest.raises(PrettyPrintError, match="disk full"):
            progress()[0]()
    assert path.read_bytes() == original
    assert len(list(images.rglob("*.dcm"))) == 6
    assert not list(path.parent.glob("*.tmp"))


def test_default_media_callbacks_keep_existing_serialization(tmp_path):
    import orjson

    path, images = _media_annotation(tmp_path)
    expected = json.loads(path.read_bytes())
    progress, count = download_all_images_from_annotations(
        _MediaClient(), path.parent, images
    )
    tasks = progress()
    assert count == len(tasks) == 6
    for task in tasks:
        task()
    for slot in expected["item"]["slots"]:
        for source in slot["source_files"]:
            source["local_path"] = str(
                images / "nested/item.jpg" / slot["slot_name"] / source["file_name"]
            )
    assert path.read_bytes() == orjson.dumps(expected, orjson.OPT_INDENT_2)


@pytest.mark.parametrize("multi_processed", [False, True])
def test_group_reports_every_download_failure(tmp_path, multi_processed):
    path, images = _media_annotation(tmp_path)
    failed_urls = ("http://media/z/a", "http://media/z/m")
    progress, _ = download_all_images_from_annotations(
        _MediaClient(failed_urls), path.parent, images, pretty_print=True
    )
    tasks = progress()
    _, errors = exhaust_generator(tasks, len(tasks), multi_processed, worker_count=2)
    assert len(errors) == 1
    assert all(url in str(errors[0]) for url in failed_urls)
    sources = json.loads(path.read_bytes())["item"]["slots"][0]["source_files"]
    assert Path(sources[0]["local_path"]).read_bytes() == b"media bytes"
    assert sources[1]["local_path"] == "another old path"
    assert "local_path" not in sources[2]


@pytest.mark.usefixtures("file_read_write_test")
def test_pull_propagates_trace_formatting_error(remote_dataset):
    import darwin.dataset.json_formatter as formatter

    with zipfile.ZipFile("tests/dataset_with_properties.zip") as archive:
        original = archive.read("ferrari-laferrari.json")
    release = Release(
        remote_dataset.slug,
        remote_dataset.team,
        "0.1.0",
        "trace-format-error",
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

    original_replace = formatter.os.replace
    replacements = []

    def fail_trace_replace(source, destination):
        replacements.append(destination)
        if len(replacements) == 2:
            raise OSError("trace disk full")
        return original_replace(source, destination)

    response = MagicMock(ok=True, headers={"Content-Type": "image/jpeg"})
    response.__iter__.return_value = [b"media bytes"]
    with (
        patch.object(Release, "download_zip", side_effect=download_zip),
        patch.object(
            remote_dataset.client, "_get_raw_from_full_url", return_value=response
        ),
        patch.object(formatter.os, "replace", side_effect=fail_trace_replace),
        pytest.raises(PrettyPrintError, match="trace disk full"),
    ):
        remote_dataset.pull(release=release, pretty_print=True, multi_processed=False)
    assert len(replacements) == 2
    output = next(
        (remote_dataset.local_releases_path / release.name / "annotations").glob(
            "*.json"
        )
    )
    assert json.loads(output.read_bytes()) == json.loads(original)
    assert not list(output.parent.glob("*.tmp"))


@pytest.mark.parametrize("multi_processed", [False, True])
def test_pretty_media_factory_serializes_two_annotations_for_external_pool(
    tmp_path, multi_processed
):
    first, images = _media_annotation(tmp_path)
    second = first.with_name("second.json")
    second.write_bytes(first.read_bytes().replace(b"item.jpg", b"second.jpg"))
    progress, count = download_all_images_from_annotations(
        _MediaClient(), first.parent, images, pretty_print=True
    )
    tasks = list(progress())
    assert count == 12
    assert len(tasks) == 1
    successes, errors = exhaust_generator(
        tasks, len(tasks), multi_processed, worker_count=2
    )
    assert len(successes) == 1
    assert errors == []
    for annotation in (first, second):
        output = annotation.read_bytes()
        assert b"1.0000" in output
        assert b'"\\u0061\\/"' in output
        for slot in json.loads(output)["item"]["slots"]:
            for source in slot["source_files"]:
                assert Path(source["local_path"]).read_bytes() == b"media bytes"
    assert len(list(images.rglob("*.dcm"))) == count


@pytest.mark.usefixtures("file_read_write_test")
@pytest.mark.parametrize("blocking", [False, True])
@pytest.mark.parametrize("multi_processed", [False, True])
def test_two_annotation_pull_uses_one_serial_media_task(
    remote_dataset, blocking, multi_processed
):
    with zipfile.ZipFile("tests/dataset_with_properties.zip") as archive:
        first = archive.read("ferrari-laferrari.json")
    first = first.rstrip()[:-1] + b',"precision":1.0000,"escaped":"\\u0061\\/"}'
    second = first.replace(b"ferrari-laferrari.jpg", b"second.jpg")
    release = Release(
        remote_dataset.slug,
        remote_dataset.team,
        "0.1.0",
        "serial-two-annotations",
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
            archive.writestr("first.json", first)
            archive.writestr("second.json", second)
        return path

    response = MagicMock(ok=True, headers={"Content-Type": "image/jpeg"})
    response.__iter__.return_value = [b"media bytes"]
    with (
        patch.object(Release, "download_zip", side_effect=download_zip),
        patch.object(
            remote_dataset.client, "_get_raw_from_full_url", return_value=response
        ),
        patch(
            "darwin.dataset.utils.mp.Pool",
            side_effect=AssertionError("unexpected parallel media"),
        ),
    ):
        progress, count = remote_dataset.pull(
            release=release,
            pretty_print=True,
            blocking=blocking,
            multi_processed=multi_processed,
        )
        if not blocking:
            tasks = list(progress())
            assert len(tasks) == 1
            tasks[0]()
    assert count == 2
    annotations = remote_dataset.local_releases_path / release.name / "annotations"
    outputs = list(annotations.glob("*.json"))
    assert len(outputs) == 2
    for output in outputs:
        raw = output.read_bytes()
        assert b"1.0000" in raw
        assert b'"\\u0061\\/"' in raw
        parsed = json.loads(raw)
        source = parsed["item"]["slots"][0]["source_files"][0]
        local_path = Path(source.pop("local_path"))
        assert local_path.name == parsed["item"]["name"]
        assert local_path.read_bytes() == b"media bytes"
        assert parsed == json.loads(
            first if local_path.name == "ferrari-laferrari.jpg" else second
        )


@pytest.mark.parametrize("multi_processed", [False, True])
def test_serial_media_continues_after_failures_in_both_annotations(
    tmp_path, multi_processed
):
    first, images = _media_annotation(tmp_path)
    second = first.with_name("second.json")
    second.write_bytes(
        first.read_bytes()
        .replace(b"item.jpg", b"second.jpg")
        .replace(b"http://media/", b"http://second/")
    )
    failed_urls = ("http://media/z/a", "http://second/z/m")
    progress, count = download_all_images_from_annotations(
        _MediaClient(failed_urls), first.parent, images, pretty_print=True
    )
    tasks = list(progress())
    assert len(tasks) == 1
    _, errors = exhaust_generator(tasks, len(tasks), multi_processed, worker_count=2)
    assert len(errors) == 1
    assert all(url in str(errors[0]) for url in failed_urls)
    assert count == 12
    assert len(list(images.rglob("*.dcm"))) == 10
    for annotation in (first, second):
        for slot in json.loads(annotation.read_bytes())["item"]["slots"]:
            for source in slot["source_files"]:
                if source["url"] not in failed_urls:
                    assert Path(source["local_path"]).read_bytes() == b"media bytes"
    assert b"1.0000" in first.read_bytes()
    assert b"1.0000" in second.read_bytes()


def test_serial_media_preserves_format_error_type_and_later_download_errors(tmp_path):
    import darwin.dataset.json_formatter as formatter

    first, images = _media_annotation(tmp_path)
    original = first.read_bytes()
    second = first.with_name("second.json")
    second.write_bytes(
        original.replace(b"item.jpg", b"second.jpg").replace(
            b"http://media/", b"http://second/"
        )
    )
    failed_url = "http://second/z/m"
    progress, count = download_all_images_from_annotations(
        _MediaClient((failed_url,)), first.parent, images, pretty_print=True
    )
    original_replace = formatter.os.replace

    def fail_first(source, destination):
        if destination == first:
            raise OSError("first annotation disk full")
        original_replace(source, destination)

    tasks = list(progress())
    with patch.object(formatter.os, "replace", side_effect=fail_first):
        _, errors = exhaust_generator(tasks, len(tasks), multi_processed=False)
    assert count == 12
    assert len(errors) == 1
    assert isinstance(errors[0], PrettyPrintError)
    assert "first annotation disk full" in str(errors[0])
    assert failed_url in str(errors[0])
    assert first.read_bytes() == original
    assert len(list(images.rglob("*.dcm"))) == 11
    assert b'"local_path"' in second.read_bytes()
    assert b"1.0000" in second.read_bytes()
