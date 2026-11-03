import json
from pathlib import Path

import pytest

from darwin.dataset.utils import _map_annotations_to_images, get_annotations


def _annotation(name: str, path: str, source_file: str | None = None) -> dict:
    return {
        "version": "2.0",
        "annotations": [],
        "item": {
            "name": name,
            "path": path,
            "slots": [
                {
                    "type": "image",
                    "slot_name": "0",
                    "width": 4,
                    "height": 4,
                    "source_files": [{"file_name": source_file or name}],
                }
            ],
        },
    }


def _dataset(tmp_path: Path, annotations: dict[str, dict]) -> Path:
    release = tmp_path / "releases" / "latest"
    annotations_dir = release / "annotations"
    annotations_dir.mkdir(parents=True)
    (release / "lists").mkdir()
    (release / "lists" / "classes_polygon.txt").write_text("vessel\n")
    for filename, payload in annotations.items():
        (annotations_dir / filename).write_text(json.dumps(payload))
    (tmp_path / "images").mkdir()
    return tmp_path


def _file_names(dataset: Path) -> list[str]:
    records = list(
        get_annotations(
            dataset,
            release_name="latest",
            annotation_type="polygon",
            annotation_format="coco",
            ignore_inconsistent_examples=True,
        )
    )
    return [record["file_name"] for record in records]


def test_flat_pull_maps_root_image(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path, {"scan.json": _annotation("scan.jpg", "/")})
    image = dataset / "images" / "scan.jpg"
    image.write_bytes(b"img")

    assert _file_names(dataset) == [str(image)]


def test_folder_pull_maps_image_under_item_path(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path, {"scan.json": _annotation("scan.jpg", "/studies/oct")})
    image = dataset / "images" / "studies" / "oct" / "scan.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"img")

    assert _file_names(dataset) == [str(image)]


def test_sibling_directory_does_not_invalidate_flat_images(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path,
        {
            "a.json": _annotation("scan_a.jpg", "/studies/oct"),
            "b.json": _annotation("scan_b.jpg", "/studies/oct"),
        },
    )
    images = dataset / "images"
    (images / "scan_a.jpg").write_bytes(b"a")
    (images / "scan_b.jpg").write_bytes(b"b")
    series = images / "other_series"
    series.mkdir()
    (series / "slice.dcm").write_bytes(b"dcm")

    assert sorted(Path(path).name for path in _file_names(dataset)) == [
        "scan_a.jpg",
        "scan_b.jpg",
    ]


def _mapped_images(dataset: Path) -> list[Path]:
    annotation_paths = sorted(
        (dataset / "releases" / "latest" / "annotations").glob("*.json")
    )
    images, _, invalid, _ = _map_annotations_to_images(
        (str(path) for path in annotation_paths),
        dataset / "images",
        True,
    )
    assert invalid == []
    return images


def test_multifile_dicom_directory_maps_to_first_slice(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path, {"series.json": _annotation("series.dcm", "/", "series.dcm")}
    )
    series = dataset / "images" / "series"
    series.mkdir()
    (series / "slice_002.dcm").write_bytes(b"2")
    (series / "slice_001.dcm").write_bytes(b"1")

    assert _mapped_images(dataset) == [series / "slice_001.dcm"]


def test_flat_dicom_directory_maps_when_item_path_is_nested(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path,
        {"series.json": _annotation("series.dcm", "/studies/oct", "series.dcm")},
    )
    series = dataset / "images" / "series"
    series.mkdir()
    (series / "slice_001.dcm").write_bytes(b"1")

    assert _mapped_images(dataset) == [series / "slice_001.dcm"]


def test_multifile_dicom_under_item_path_maps_to_slice(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path,
        {"series.json": _annotation("series.dcm", "/studies/oct", "series.dcm")},
    )
    series = dataset / "images" / "studies" / "oct" / "series"
    series.mkdir(parents=True)
    (series / "slice_001.dcm").write_bytes(b"1")

    assert _mapped_images(dataset) == [series / "slice_001.dcm"]


def test_slot_directory_layout_maps_source_file(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path, {"series.json": _annotation("series.dcm", "/", "slice_001.dcm")}
    )
    image = dataset / "images" / "series.dcm" / "0" / "slice_001.dcm"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"1")

    assert _mapped_images(dataset) == [image]


def test_all_inconsistent_error_names_the_mismatch(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path,
        {
            "a.json": _annotation("missing_a.jpg", "/studies/oct"),
            "b.json": _annotation("missing_b.jpg", "/studies/oct"),
        },
    )
    series = dataset / "images" / "unrelated_series"
    series.mkdir()
    (series / "slice.dcm").write_bytes(b"x")

    with pytest.raises(ValueError) as exc_info:
        _file_names(dataset)

    message = str(exc_info.value)
    assert "Could not find any" not in message
    assert "with_folders=True" in message
    assert "missing_a.jpg" in message
    assert "unrelated_series" in message


def test_empty_images_dir_still_reports_no_media(tmp_path: Path) -> None:
    dataset = _dataset(tmp_path, {"a.json": _annotation("missing.jpg", "/")})

    with pytest.raises(ValueError, match="Could not find any"):
        _file_names(dataset)


def _unmapped(dataset: Path) -> list[str]:
    annotation_paths = sorted(
        (dataset / "releases" / "latest" / "annotations").glob("*.json")
    )
    images, _, invalid, _ = _map_annotations_to_images(
        (str(path) for path in annotation_paths),
        dataset / "images",
        True,
    )
    assert images == []
    return [Path(path).name for path in invalid]


def test_folder_series_wins_over_same_name_root_file(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path, {"scan.json": _annotation("scan.dcm", "/studies", "scan.dcm")}
    )
    images = dataset / "images"
    (images / "scan.dcm").write_bytes(b"root item")
    series = images / "studies" / "scan"
    series.mkdir(parents=True)
    (series / "slice_001.dcm").write_bytes(b"1")

    assert _mapped_images(dataset) == [series / "slice_001.dcm"]


def test_folder_slot_file_wins_over_same_name_root_file(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path, {"scan.json": _annotation("scan.jpg", "/studies", "source.jpg")}
    )
    images = dataset / "images"
    (images / "scan.jpg").write_bytes(b"root item")
    slot_file = images / "studies" / "scan.jpg" / "0" / "source.jpg"
    slot_file.parent.mkdir(parents=True)
    slot_file.write_bytes(b"slot")

    assert _mapped_images(dataset) == [slot_file]


def test_multi_slot_item_is_not_mapped_to_one_slot(tmp_path: Path) -> None:
    payload = _annotation("pair.jpg", "/", "left.jpg")
    second_slot = dict(payload["item"]["slots"][0])
    second_slot.update(slot_name="1", source_files=[{"file_name": "right.jpg"}])
    payload["item"]["slots"].append(second_slot)
    dataset = _dataset(tmp_path, {"pair.json": payload})
    for slot_name, file_name in (("0", "left.jpg"), ("1", "right.jpg")):
        image = dataset / "images" / "pair.jpg" / slot_name / file_name
        image.parent.mkdir(parents=True)
        image.write_bytes(b"img")

    assert _unmapped(dataset) == ["pair.json"]


def test_extracted_video_frames_are_not_mapped(tmp_path: Path) -> None:
    payload = _annotation("clip.mp4", "/", "clip.mp4")
    payload["item"]["slots"][0]["type"] = "video"
    dataset = _dataset(tmp_path, {"clip.json": payload})
    frames = dataset / "images" / "clip"
    frames.mkdir()
    (frames / "0000000.png").write_bytes(b"frame")

    assert _unmapped(dataset) == ["clip.json"]


def test_slot_layout_uses_sanitized_names(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path, {"series.json": _annotation("series.dcm", "/", "slice?001.dcm")}
    )
    image = dataset / "images" / "series.dcm" / "0" / "slice_001.dcm"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"1")

    assert _mapped_images(dataset) == [image]


def test_series_directory_without_media_is_skipped(tmp_path: Path) -> None:
    dataset = _dataset(
        tmp_path, {"series.json": _annotation("series.dcm", "/studies", "series.dcm")}
    )
    images = dataset / "images"
    folder_series = images / "studies" / "series"
    folder_series.mkdir(parents=True)
    (folder_series / "README").write_text("notes")
    (folder_series / ".DS_Store").write_bytes(b"x")
    root_series = images / "series"
    root_series.mkdir()
    (root_series / "slice_001.dcm").write_bytes(b"1")

    assert _mapped_images(dataset) == [root_series / "slice_001.dcm"]
