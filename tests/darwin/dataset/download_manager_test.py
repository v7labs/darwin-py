from pathlib import Path
from typing import Callable, List
from unittest.mock import MagicMock

import pytest
import responses

from darwin.dataset import download_manager as dm
from darwin.datatypes import AnnotationClass, AnnotationFile, Slot, SourceFile
from tests.fixtures import *
from darwin.client import Client
from darwin.exceptions import MediaNotReady
from darwin.config import Config


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


@pytest.fixture
def darwin_client(
    darwin_config_path: Path,
    darwin_datasets_path: Path,
    team_slug_darwin_json_v2: str,
) -> Client:
    config = Config(darwin_config_path)
    config.put(["global", "api_endpoint"], "http://localhost/api")
    config.put(["global", "base_url"], "http://localhost")
    config.put(["teams", team_slug_darwin_json_v2, "api_key"], "mock_api_key")
    config.put(
        ["teams", team_slug_darwin_json_v2, "datasets_dir"],
        str(darwin_datasets_path),
    )
    return Client(config)


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


@pytest.mark.usefixtures("file_read_write_test")
def test_get_segment_manifests(
    manifest_paths: List[Path],
    slot_w_manifests: Slot,
    darwin_client: Client,
    file_read_write_test,
) -> None:
    parent_path = Path("tests/darwin/dataset/data/manifest_examples")
    files = [open(path, "r").read() for path in manifest_paths]
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, "http://test.com", body=files[0])
        rsps.add(responses.GET, "http://test2.com", body=files[1])
        segment_manifests = dm.get_segment_manifests(
            slot_w_manifests, parent_path, darwin_client
        )
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
                source_files=[SourceFile(file_name="source_name.jpg")],
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
                source_files=[SourceFile(file_name="source_name.jpg")],
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
                source_files=[
                    SourceFile(file_name="source_name_1.jpg"),
                ],
            ),
            Slot(
                name="slot2",
                type="image",
                source_files=[SourceFile(file_name="source_name_2.jpg")],
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
                source_files=[SourceFile(file_name="source_name_1.jpg")],
            ),
            Slot(
                name="slot2",
                type="image",
                source_files=[SourceFile(file_name="source_name_2.jpg")],
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
                source_files=[SourceFile(file_name="source_name.jpg")],
            )
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")
    result = dm._get_planned_image_paths(annotation, images_path, use_folders=True)
    expected = [images_path / "image.jpg"]
    assert result == expected


def test_dicom_series_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/series.json"),
        filename="series.dcm",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="slot1",
                type="dicom",
                source_files=[
                    SourceFile(file_name="slice_1.dcm"),
                    SourceFile(file_name="slice_2.dcm"),
                    SourceFile(file_name="slice_3.dcm"),
                ],
            )
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")
    results = dm._get_planned_image_paths(annotation, images_path, use_folders=False)
    expected = [
        images_path / "series.dcm" / "slot1" / "slice_1.dcm",
        images_path / "series.dcm" / "slot1" / "slice_2.dcm",
        images_path / "series.dcm" / "slot1" / "slice_3.dcm",
    ]
    assert results == expected


def test_extracted_frames_planned_image_paths():
    annotation = AnnotationFile(
        path=Path("/local/annotations/video.json"),
        filename="video.mp4",
        annotation_classes={
            AnnotationClass(name="test_class", annotation_type="polygon")
        },
        annotations=[],
        slots=[
            Slot(
                name="0",
                type="image",
                source_files=[
                    SourceFile(file_name="frame_0.jpg"),
                    SourceFile(file_name="video.mp4"),
                ],
            ),
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")
    results = dm._get_planned_image_paths(annotation, images_path, use_folders=False)
    expected = [
        images_path / "video.mp4" / "0" / "frame_0.jpg",
    ]
    assert results == expected


def test_multiple_source_files_raises_error():
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
                    SourceFile(file_name="image1.jpg"),
                    SourceFile(file_name="image2.jpg"),
                ],
            )
        ],
        remote_path="/",
    )
    images_path = Path("/local/images")

    with pytest.raises(ValueError) as exc_info:
        dm._get_planned_image_paths(annotation, images_path, use_folders=False)

    assert (
        str(exc_info.value)
        == "This slot contains data that is not a DICOM series or a frame extracted from a video"
    )


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
    assert (
        "Warning: Identical filenames detected in your export release."
        not in captured.out
    )


def test__check_for_duplicate_local_filepaths_single_duplicate(capsys):
    download_functions = [
        create_mock_download_function("path/to/file1.jpg"),
        create_mock_download_function("path/to/file2.jpg"),
        create_mock_download_function("path/to/file1.jpg"),
    ]
    dm._check_for_duplicate_local_filepaths(download_functions)
    captured = capsys.readouterr()
    assert (
        "Warning: Identical filenames detected in your export release." in captured.out
    )
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
    assert (
        "Warning: Identical filenames detected in your export release." in captured.out
    )
    assert "path/to/file1.jpg is duplicated 2 times" in captured.out
    assert "path/to/file3.jpg is duplicated 3 times" in captured.out


FRAME_URL = "http://localhost/api/v2/teams/t/files/f/sections/0"


@pytest.fixture
def sleeps(monkeypatch) -> List[float]:
    slept: List[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    monkeypatch.setattr("time.monotonic", lambda: sum(slept))
    return slept


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_download_image_waits_retry_after_for_frame_being_prepared(
    darwin_client: Client, tmp_path: Path, sleeps: List[float], capsys
) -> None:
    responses.add(responses.GET, FRAME_URL, status=503, headers={"Retry-After": "7"})
    responses.add(
        responses.GET,
        FRAME_URL,
        status=503,
        headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},
    )
    responses.add(responses.GET, FRAME_URL, status=503, headers={"Retry-After": "0"})
    responses.add(responses.GET, FRAME_URL, status=200, body=b"frame")
    path = tmp_path / "0000000.png"

    dm._download_image(FRAME_URL, path, darwin_client)

    assert path.read_bytes() == b"frame"
    assert sleeps == [7, 1, 1]
    assert (
        f"Waiting for {FRAME_URL} to be prepared, retry in 7s"
        in capsys.readouterr().out
    )


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_download_image_fails_clearly_when_retry_after_budget_exhausted(
    darwin_client: Client, tmp_path: Path, sleeps: List[float]
) -> None:
    responses.add(responses.GET, FRAME_URL, status=503, headers={"Retry-After": "600"})

    with pytest.raises(
        Exception,
        match="still being prepared after 1800s, next retry would pass the 1800s budget",
    ):
        dm._download_image(FRAME_URL, tmp_path / "0000000.png", darwin_client)

    assert sleeps == [600, 600, 600]
    assert len(responses.calls) == 4


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_retry_after_budget_counts_time_spent_in_5xx_backoff(
    darwin_client: Client, tmp_path: Path, sleeps: List[float]
) -> None:
    responses.add(responses.GET, FRAME_URL, status=502)
    responses.add(responses.GET, FRAME_URL, status=503, headers={"Retry-After": "600"})

    with pytest.raises(Exception, match="next retry would pass the 1800s budget"):
        dm._download_image(FRAME_URL, tmp_path / "0000000.png", darwin_client)

    assert sleeps[0] >= 60 and sleeps[1:] == [600, 600]


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_5xx_after_retry_after_shares_the_budget_and_hides_the_token(
    darwin_client: Client, tmp_path: Path, sleeps: List[float], capsys
) -> None:
    url = f"{FRAME_URL}?token=secret"
    responses.add(responses.GET, url, status=503, headers={"Retry-After": "600"})
    responses.add(responses.GET, url, status=502)

    with pytest.raises(MediaNotReady, match="still being prepared") as error:
        dm._download_image(url, tmp_path / "0000000.png", darwin_client)

    assert sleeps[0] == 600 and sum(sleeps) <= 1800
    assert "secret" not in str(error.value) + capsys.readouterr().out


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_download_image_4xx_is_fatal_even_with_retry_after(
    darwin_client: Client, tmp_path: Path, sleeps: List[float]
) -> None:
    responses.add(responses.GET, FRAME_URL, status=403, headers={"Retry-After": "1"})

    with pytest.raises(Exception):
        dm._download_image(FRAME_URL, tmp_path / "0000000.png", darwin_client)

    assert sleeps == []
    assert len(responses.calls) == 1


@pytest.mark.usefixtures("file_read_write_test")
@responses.activate
def test_download_image_other_5xx_keep_exponential_backoff(
    darwin_client: Client, tmp_path: Path, sleeps: List[float]
) -> None:
    responses.add(responses.GET, FRAME_URL, status=502, headers={"Retry-After": "1"})
    responses.add(responses.GET, FRAME_URL, status=200, body=b"frame")

    dm._download_image(FRAME_URL, tmp_path / "0000000.png", darwin_client)

    assert len(sleeps) == 1 and sleeps[0] >= 60


def _video_annotation(slot_names: List[str]) -> AnnotationFile:
    return AnnotationFile(
        path=Path("/local/annotations/video.json"),
        filename="video.mp4",
        annotation_classes=set(),
        annotations=[],
        slots=[
            Slot(name=name, type="video", source_files=[], frame_urls=[FRAME_URL])
            for name in slot_names
        ],
        remote_path="/",
    )


@pytest.mark.usefixtures("file_read_write_test")
@pytest.mark.parametrize(
    "build",
    [
        lambda client, path: dm._download_single_slot_from_json_annotation(
            _video_annotation(["0"]), client, path, path / "video.json", True
        ),
        lambda client, path: dm._download_all_slots_from_json_annotation(
            _video_annotation(["0", "1"]), client, path, True
        ),
    ],
    ids=["single_slot", "multi_slot"],
)
@responses.activate
def test_frame_downloads_wait_retry_after_on_every_slot_path(
    darwin_client: Client, tmp_path: Path, sleeps: List[float], build
) -> None:
    responses.add(responses.GET, FRAME_URL, status=503, headers={"Retry-After": "5"})
    responses.add(responses.GET, FRAME_URL, status=200, body=b"frame")

    downloads = build(darwin_client, tmp_path)
    for download in downloads:
        download()

    assert sleeps == [5]
    assert [p.read_bytes() for p in tmp_path.rglob("*.png")] == [b"frame"] * len(
        downloads
    )


def test_raise_media_errors_keeps_media_not_ready() -> None:
    from darwin.exceptions import MediaNotReady

    with pytest.raises(MediaNotReady, match="frame 1"):
        dm._raise_media_errors([Exception("other"), MediaNotReady("frame 1")])
