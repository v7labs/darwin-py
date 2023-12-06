from pathlib import Path, PurePosixPath

from darwin.path_utils import construct_full_path, deconstruct_full_path, parse_manifest


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
