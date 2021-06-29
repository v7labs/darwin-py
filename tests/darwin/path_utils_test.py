from pathlib import PurePosixPath

from darwin.path_utils import construct_full_path


def test_os_path_construction():
    # A quick reference for expected behavior of (PurePosixPath
    assert "/test/foo.bar" == (PurePosixPath("/") / 'test' / 'foo.bar').as_posix()
    assert "/" == (PurePosixPath("/") / "/").as_posix()
    assert "/file.name" == (PurePosixPath("/") / "file.name").as_posix()
    assert "file.name" == (PurePosixPath("") / "file.name").as_posix()
    assert "/file.name" == (PurePosixPath("") / "/file.name").as_posix()
    assert "/file.name" == (PurePosixPath("/") / "/file.name").as_posix()
    # note; this is not in /one path
    assert "/file.name" == (PurePosixPath("/one") / "/file.name").as_posix()
    assert "/one/file.name" == (PurePosixPath("/one") / "file.name").as_posix()
    assert "/one/file.name" == (PurePosixPath("/one/") / "file.name").as_posix()
    assert "/one/two/file.name" == (PurePosixPath("/") / "one/two/" / "file.name").as_posix()
    assert "/one/two/file.name" == (PurePosixPath("/") / "/one/two/" / "file.name").as_posix()
    assert "/one/two/file.name" == (PurePosixPath("/") / "/one/two" / "file.name").as_posix()
    assert "/one/two/three/file.name" == (PurePosixPath("/") / "one/" / "two/" / "three/" "file.name").as_posix()
    
    assert "onlyfile.name" == construct_full_path(None, "onlyfile.name")
