from pathlib import Path
from typing import Callable, List
from unittest.mock import MagicMock

import pytest
import responses

from darwin.dataset import download_manager as dm
from darwin.datatypes import AnnotationClass, AnnotationFile, Slot
from tests.fixtures import *


@pytest.fixture
def manifest_paths() -> List[Path]:
    return [
        Path("tests/darwin/dataset/data/manifest_examples/manifest_1.txt.test"),
        Path("tests/darwin/dataset/data/manifest_examples/manifest_2.txt.test"),
    ]


@pytest.fixture
def slot_w_manifests() -> Slot:
    return Slot(
        name="test_slot",
        type="video",
        source_files=[],
        frame_manifest=[{"url": "http://test.com"}, {"url": "http://test2.com"}],
    )


def test_parse_manifests(manifest_paths: List[Path]) -> None:
    segment_manifests = dm._parse_manifests(manifest_paths, "0")
    assert len(segment_manifests) == 4
    assert len(segment_manifests[0].items) == 2
    assert len(segment_manifests[1].items) == 2
    assert len(segment_manifests[2].items) == 2
    assert len(segment_manifests[3].items) == 2
    assert segment_manifests[0].items[0].absolute_frame == 0
    assert segment_manifests[0].items[1].absolute_frame == 1
    assert segment_manifests[0].items[1].visibility is True
    assert segment_manifests[1].items[0].absolute_frame == 2
    assert segment_manifests[1].items[1].absolute_frame == 3
    assert segment_manifests[1].items[1].visibility is True
    assert segment_manifests[2].items[0].absolute_frame == 4
    assert segment_manifests[2].items[1].absolute_frame == 5
    assert segment_manifests[2].items[1].visibility is True
    assert segment_manifests[3].items[0].absolute_frame == 6
    assert segment_manifests[3].items[1].absolute_frame == 7
    assert segment_manifests[3].items[1].visibility is True


def test_get_segment_manifests(
    manifest_paths: List[Path], slot_w_manifests: Slot
) -> None:
    parent_path = Path("tests/darwin/dataset/data/manifest_examples")
    files = [open(path, "r").read() for path in manifest_paths]
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://test.com", body=files[0])
        rsps.add(responses.GET, "http://test2.com", body=files[1])
        segment_manifests = dm.get_segment_manifests(slot_w_manifests, parent_path, "")
        assert len(segment_manifests) == 4
        assert len(segment_manifests[0].items) == 2
        assert len(segment_manifests[1].items) == 2
        assert len(segment_manifests[2].items) == 2
        assert len(segment_manifests[3].items) == 2
        assert segment_manifests[0].items[0].absolute_frame == 0
        assert segment_manifests[0].items[1].absolute_frame == 1
        assert segment_manifests[0].items[1].visibility is True
        assert segment_manifests[1].items[0].absolute_frame == 2
        assert segment_manifests[1].items[1].absolute_frame == 3
        assert segment_manifests[1].items[1].visibility is True
        assert segment_manifests[2].items[0].absolute_frame == 4
        assert segment_manifests[2].items[1].absolute_frame == 5
        assert segment_manifests[2].items[1].visibility is True
        assert segment_manifests[3].items[0].absolute_frame == 6
        assert segment_manifests[3].items[1].absolute_frame == 7
        assert segment_manifests[3].items[1].visibility is True


def test_single_slot_without_folders_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/image.json"),
        filename="image.jpg",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="image",
                source_files=[{"file_name": "source_name.jpg"}],
            )
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")
    result = dm._get_planned_image_paths(annotation, images_path, use_folders=False)
    expected = [images_path / "image.jpg"]
    assert result == expected


def test_single_slot_with_folders_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/image.json"),
        filename="image.jpg",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="image",
                source_files=[{"file_name": "source_name.jpg"}],
            )
        ],
        remote_path="/remote/path",
    )
    images_path = Path("/local/images")
    result = dm._get_planned_image_paths(annotation, images_path, use_folders=True)
    expected = [images_path / "remote/path/image.jpg"]
    assert result == expected


def test_multi_slot_without_folders_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/image.json"),
        filename="image.jpg",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="image",
                source_files=[{"file_name": "source_name_1.jpg"}],
            ),
            Slot(
                name="slot2",
                type="image",
                source_files=[{"file_name": "source_name_2.jpg"}],
            ),
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")
    result = dm._get_planned_image_paths(annotation, images_path, use_folders=False)
    expected = [
        images_path / "image.jpg" / "slot1" / "source_name_1.jpg",
        images_path / "image.jpg" / "slot2" / "source_name_2.jpg",
    ]
    assert result == expected


def test_multi_slot_with_folders_planned_image_path():
    annotation = AnnotationFile(
        path=Path("/local/annotations/image.json"),
        filename="image.jpg",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="image",
                source_files=[{"file_name": "source_name_1.jpg"}],
            ),
            Slot(
                name="slot2",
                type="image",
                source_files=[{"file_name": "source_name_2.jpg"}],
            ),
        ],
        remote_path="/remote/path",
    )
    images_path = Path("/local/images")
    result = dm._get_planned_image_paths(annotation, images_path, use_folders=True)
    expected = [
        images_path / "remote/path" / "image.jpg" / "slot1" / "source_name_1.jpg",
        images_path / "remote/path" / "image.jpg" / "slot2" / "source_name_2.jpg",
    ]
    assert result == expected


def test_single_slot_root_path_with_folders_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/image.json"),
        filename="image.jpg",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="image",
                source_files=[{"file_name": "source_name.jpg"}],
            )
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")
    result = dm._get_planned_image_paths(annotation, images_path, use_folders=True)
    expected = [images_path / "image.jpg"]
    assert result == expected


def test_multiple_source_files_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/image.json"),
        filename="image.jpg",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="image",
                source_files=[
                    {"file_name": "source_name_1.jpg"},
                    {"file_name": "source_name_2.jpg"},
                ],
            )
        ],
    )
    images_path = Path("/local/images")
    results = dm._get_planned_image_paths(annotation, images_path, use_folders=False)
    expected = [
        images_path / "image.jpg" / "slot1" / "source_name_1.jpg",
        images_path / "image.jpg" / "slot1" / "source_name_2.jpg",
    ]
    assert results == expected


def test__remove_empty_directories(tmp_path: Path) -> None:
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    subdir_1 = root_dir / "subdir_1"
    subdir_1.mkdir()
    subdir_2 = root_dir / "subdir_2"
    subdir_2.mkdir()
    nested_subdir = subdir_1 / "nested_subdir"
    nested_subdir.mkdir()

    (subdir_2 / "file.txt").write_text("This is a test file")
    (nested_subdir / ".DS_Store").write_text("This is a .DS_Store file")

    assert subdir_1.exists()
    assert subdir_2.exists()
    assert nested_subdir.exists()

    dm._remove_empty_directories(root_dir)

    assert not nested_subdir.exists()
    assert subdir_1.exists()
    assert subdir_2.exists()
    assert (subdir_1 / ".DS_Store").exists() is False


def test__remove_empty_directories_with_no_empty_dirs(tmp_path: Path) -> None:
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    subdir_1 = root_dir / "subdir_1"
    subdir_1.mkdir()
    subdir_2 = root_dir / "subdir_2"
    subdir_2.mkdir()
    (subdir_1 / "file1.txt").write_text("File in subdir_1")
    (subdir_2 / "file2.txt").write_text("File in subdir_2")

    dm._remove_empty_directories(root_dir)

    assert subdir_1.exists()
    assert subdir_2.exists()


def test__remove_empty_directories_all_empty(tmp_path: Path) -> None:
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    subdir_1 = root_dir / "subdir_1"
    subdir_1.mkdir()
    subdir_2 = root_dir / "subdir_2"
    subdir_2.mkdir()

    dm._remove_empty_directories(root_dir)

    assert not subdir_1.exists()
    assert not subdir_2.exists()


def test_remove_empty_directories_with_ds_store(tmp_path: Path) -> None:
    root_dir = tmp_path / "root"
    root_dir.mkdir()
    subdir_1 = root_dir / "subdir_1"
    subdir_1.mkdir()
    (subdir_1 / ".DS_Store").write_text("This is a .DS_Store file")

    dm._remove_empty_directories(root_dir)

    assert not subdir_1.exists()


def create_mock_download_function(filepath: str) -> Callable[[], None]:
    mock_func = MagicMock()
    mock_func.args = [None, None, filepath]
    return mock_func


def test__check_for_duplicate_local_filepaths_no_duplicates(capsys):
    download_functions = [
        create_mock_download_function("path/to/file1.jpg"),
        create_mock_download_function("path/to/file2.jpg"),
        create_mock_download_function("path/to/file3.jpg"),
    ]
    dm._check_for_duplicate_local_filepaths(download_functions)
    captured = capsys.readouterr()
    assert "Warning: Duplicate download paths detected" not in captured.out


def test__check_for_duplicate_local_filepaths_single_duplicate(capsys):
    download_functions = [
        create_mock_download_function("path/to/file1.jpg"),
        create_mock_download_function("path/to/file2.jpg"),
        create_mock_download_function("path/to/file1.jpg"),
    ]
    dm._check_for_duplicate_local_filepaths(download_functions)
    captured = capsys.readouterr()
    assert "Warning: Duplicate download paths detected" in captured.out
    assert "path/to/file1.jpg is duplicated 2 times" in captured.out


def test__check_for_duplicate_local_filepaths_multiple_duplicates(capsys):
    download_functions = [
        create_mock_download_function("path/to/file1.jpg"),
        create_mock_download_function("path/to/file2.jpg"),
        create_mock_download_function("path/to/file1.jpg"),
        create_mock_download_function("path/to/file3.jpg"),
        create_mock_download_function("path/to/file3.jpg"),
        create_mock_download_function("path/to/file3.jpg"),
    ]
    dm._check_for_duplicate_local_filepaths(download_functions)
    captured = capsys.readouterr()
    assert "Warning: Duplicate download paths detected" in captured.out
    assert "path/to/file1.jpg is duplicated 2 times" in captured.out
    assert "path/to/file3.jpg is duplicated 3 times" in captured.out
