import os

from darwin.utils import construct_full_path

def test_os_path_construction():
    # A quick reference for expected behavior of os.path.join
    assert "/" == os.path.join("/", "/")
    assert "/file.name" == os.path.join("/", "file.name")
    assert "file.name" == os.path.join("", "file.name")
    assert "/file.name" == os.path.join("", "/file.name")
    assert "/file.name" == os.path.join("/", "/file.name")
    # note; this is not in /one path
    assert "/file.name" == os.path.join("/one", "/file.name")
    assert "/one/file.name" == os.path.join("/one", "file.name")
    assert "/one/file.name" == os.path.join("/one/", "file.name")
    assert "/one/two/file.name" == os.path.join("/", "one/two/", "file.name")
    assert "/one/two/file.name" == os.path.join("/", "/one/two/", "file.name")
    assert "/one/two/file.name" == os.path.join("/", "/one/two", "file.name")
    assert "/one/two/three/file.name" == os.path.join("/", "one/", "two/", "three/" "file.name")
    
    assert "onlyfile.name" == construct_full_path(None, "onlyfile.name")
