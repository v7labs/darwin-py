import csv
from pathlib import Path
from typing import List, Optional

import pytest

from darwin.datatypes import AnnotationFile
from darwin.importer.formats.csv_tags import parse_path


class TestParsePath:
    @pytest.fixture
    def file_path(self, tmp_path: Path):
        path = tmp_path / "annotation.csv"
        yield path
        path.unlink()

    def test_it_returns_none_if_file_extension_is_not_csv(self):
        path = Path("path/to/file.xml")
        assert parse_path(path) is None

    def test_it_parses_csv_file_correctly(self, file_path: Path):
        with file_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["image1.jpg", "tag1", "tag2"])
            writer.writerow(["image2.jpg", "tag3", "tag4"])

        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        assert len(annotation_files) == 2
        assert annotation_files[0].filename == "image1.jpg"
        assert len(annotation_files[0].annotations) == 2
        assert annotation_files[1].filename == "image2.jpg"
        assert len(annotation_files[1].annotations) == 2

    def test_folders_paths_are_parsed_correctly(self, file_path: Path):
        with file_path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["folder1/folder2/image1.jpg", "tag1", "tag2"])
            writer.writerow(["folder/image2.jpg", "tag3", "tag4"])

        annotation_files: Optional[List[AnnotationFile]] = parse_path(file_path)
        assert annotation_files is not None

        assert len(annotation_files) == 2
        assert annotation_files[0].filename == "image1.jpg"
        assert annotation_files[0].remote_path == "/folder1/folder2"
        assert len(annotation_files[0].annotations) == 2
        assert annotation_files[1].filename == "image2.jpg"
        assert annotation_files[1].remote_path == "/folder"
        assert len(annotation_files[1].annotations) == 2
