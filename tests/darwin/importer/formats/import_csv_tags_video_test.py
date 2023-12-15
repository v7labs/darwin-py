import csv
from pathlib import Path
from typing import List, Optional

import pytest

import darwin.datatypes as dt
from darwin.importer.formats.csv_tags_video import parse_path


class TestParsePathVideo:
    @pytest.fixture
    def file_path(self, tmp_path: Path):
        path = tmp_path / "annotation_video.csv"
        yield path
        path.unlink()

    def test_it_returns_none_if_file_extension_is_not_csv(self):
        path = Path("path/to/file.xml")
        assert parse_path(path) is None

    def test_it_parses_csv_file_correctly(self, file_path: Path):
        with file_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["video1.mp4", "tag1", "1", "10"])
            writer.writerow(["video2.mp4", "tag2", "5", "15"])

        annotation_files: Optional[List[dt.AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        assert len(annotation_files) == 2
        assert annotation_files[0].filename == "video1.mp4"
        assert len(annotation_files[0].annotations) == 1
        assert annotation_files[1].filename == "video2.mp4"
        assert len(annotation_files[1].annotations) == 1

    def test_folders_paths_are_parsed_correctly(self, file_path: Path):
        with file_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["folder1/folder2/video1.mp4", "tag1", "1", "10"])
            writer.writerow(["folder/video2.mp4", "tag2", "5", "15"])

        annotation_files: Optional[List[dt.AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None
        assert len(annotation_files) == 2
        assert annotation_files[0].filename == "video1.mp4"
        if annotation_files[0].remote_path is not None:
            assert Path(annotation_files[0].remote_path) == Path("/folder1/folder2")
        assert len(annotation_files[0].annotations) == 1
        assert annotation_files[1].filename == "video2.mp4"
        if annotation_files[1].remote_path is not None:
            assert Path(annotation_files[1].remote_path) == Path("/folder")

    def test_keyframes_are_recorded_correctly(self, file_path: Path):
        with file_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["video1.mp4", "tag1", "1", "10"])

        annotation_files: Optional[List[dt.AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        assert len(annotation_files) == 1
        assert annotation_files[0].filename == "video1.mp4"
        assert len(annotation_files[0].annotations) == 1

        video_annotation = annotation_files[0].annotations[0]
        assert isinstance(video_annotation, dt.VideoAnnotation)

        # Check that the keyframes are recorded correctly
        assert video_annotation.keyframes == {i: i == 1 for i in range(1, 11)}
