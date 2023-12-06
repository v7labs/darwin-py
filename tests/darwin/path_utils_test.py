import shutil
import tempfile
from pathlib import Path, PurePosixPath

import pytest

from darwin.path_utils import (
    construct_full_path,
    deconstruct_full_path,
    is_properties_enabled,
    parse_manifest,
)


def test_path_construction():
    # A quick reference for expected behavior of (PurePosixPath
    assert "/test/foo.bar" == (PurePosixPath("/") / "test" / "foo.bar").as_posix()
    assert "/" == (PurePosixPath("/") / "/").as_posix()
    assert "file.name" == (PurePosixPath("") / "file.name").as_posix()
    assert "/file.name" == (PurePosixPath("") / "/file.name").as_posix()
    assert "/file.name" == (PurePosixPath("/") / "/file.name").as_posix()
    # note; this is not in /one path
    assert "/file.name" == (PurePosixPath("/one") / "/file.name").as_posix()
    assert (
        "/one/two/file.name"
        == (PurePosixPath("/") / "one/two/" / "file.name").as_posix()
    )
    assert (
        "/one/two/file.name"
        == (PurePosixPath("/") / "/one/two/" / "file.name").as_posix()
    )

    assert "onlyfile.name" == construct_full_path(None, "onlyfile.name")
    assert "/file.name" == construct_full_path("/", "file.name")
    assert "/one/file.name" == construct_full_path("one", "file.name")
    assert "/one/file.name" == construct_full_path("/one", "file.name")
    assert "/one/file.name" == construct_full_path("/one/", "file.name")
    # construct_full_path will not strip out leading slashes on filename
    assert "/file.name" == construct_full_path("/one/", "/file.name")


def test_path_deconstruction():
    assert ("/a/b", "test.png") == deconstruct_full_path("/a/b/test.png")
    assert ("/", "test.png") == deconstruct_full_path("test.png")
    assert ("/", "test.png") == deconstruct_full_path("/test.png")


def test_parse_manifest():
    manifest_path = Path(__file__).parent / "data/manifest.json"
    manifest = parse_manifest(manifest_path)

    # check that the manifest is parsed correctly
    assert len(manifest["classes"]) == 1
    assert len(manifest["classes"][0]["properties"]) == 2


@pytest.mark.parametrize(
    ("filename", "expected_bool"),
    (
        ("annotation_with_properties.json", True),
        ("annotation_without_properties.json", False),
    ),
)
def test_is_properties_enabled(filename, expected_bool):
    annotation_path = Path(__file__).parent / f"data/{filename}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmpdir_annotations = tmpdir / "annotations"
        tmpdir_annotations.mkdir(exist_ok=True)
        shutil.copy(annotation_path, tmpdir_annotations)

        assert is_properties_enabled(tmpdir) == expected_bool


@pytest.mark.parametrize(
    ("filename", "expected_bool"),
    (
        ("manifest.json", True),
        ("manifest_nested_properties.json", True),
        ("manifest_empty_properties.json", False),
    ),
)
def test_is_properties_enabled_v7(filename, expected_bool):
    manifest_path = Path(__file__).parent / f"data/{filename}"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        tmpdir_v7 = tmpdir / ".v7"
        tmpdir_v7.mkdir(exist_ok=True)
        shutil.copy(manifest_path, tmpdir_v7)

        assert is_properties_enabled(tmpdir, filename=filename) == expected_bool
