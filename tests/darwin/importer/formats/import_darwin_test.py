from pathlib import Path
from typing import Optional

import pytest
from darwin.datatypes import AnnotationFile
from darwin.importer.formats.darwin import parse_path


def describe_parse_path():
    @pytest.fixture
    def file_path(tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    def test_it_returns_none_if_there_are_no_annotations():
        path = Path("path/to/file.xml")
        assert parse_path(path) is None

    def test_it_parses_slot_names_properly_if_present_for_sequences(file_path: Path):
        json: str = """
        {
         "dataset": "test",
         "image": {
            "width": 2479,
            "height": 3508,
            "fps": 30.0,
            "original_filename": "Invoice.pdf",
            "filename": "Invoice.pdf",
            "url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/1a46356d-005b-4095-98fc-fc4ea6d7294a/original",
            "path": "/",
            "workview_url": "https://staging.v7labs.com/teams/rafals-team/items/0182e9d2-d217-3260-52db-d7828422f86b/workview",
            "frame_count": 2,
            "frame_urls": [
               "https://staging.v7labs.com/api/v2/teams/rafals-team/files/1a46356d-005b-4095-98fc-fc4ea6d7294a/sections/0",
               "https://staging.v7labs.com/api/v2/teams/rafals-team/files/1a46356d-005b-4095-98fc-fc4ea6d7294a/sections/1"
            ]
         },
         "annotations": [
            {
               "frames": {
                  "0": {
                     "bounding_box": {
                        "h": 338.29,
                        "w": 444.87,
                        "x": 845.6,
                        "y": 1056.57
                     },
                     "keyframe": true,
                     "text": {
                        "text": "some weird text"
                     }
                  }
               },
               "id": "d89a5895-c721-420b-9c7d-d71880e3679b",
               "interpolate_algorithm": "linear-1.1",
               "interpolated": true,
               "name": "address",
               "segments": [
                  [0, 2]
               ],
               "slot_names": [
                  "my_slot"
               ]
            }
         ]
         }
        """

        file_path.write_text(json)

        annotation_file: Optional[AnnotationFile] = parse_path(file_path)
        assert annotation_file is not None

        assert annotation_file.path == file_path
        assert annotation_file.filename == "Invoice.pdf"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        for annotation in annotation_file.annotations:
            assert annotation.slot_names == ["my_slot"]

    def test_it_parses_slot_names_properly_if_present_for_images(file_path: Path):
        json: str = """
         {
            "dataset": "test",
            "image": {
               "width": 500,
               "height": 375,
               "original_filename": "my_image.jpg",
               "filename": "my_image.jpg",
               "url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/d119a57f-bbbb-4b9b-a7a2-6dcb16a59e98/original",
               "thumbnail_url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/d119a57f-bbbb-4b9b-a7a2-6dcb16a59e98/thumbnail",
               "path": "/",
               "workview_url": "https://staging.v7labs.com/teams/rafals-team/items/0182e9d2-d217-681d-2448-197904d2e05c/workview"
            },
            "annotations": [
               {
                  "bounding_box": {
                  "h": 151.76,
                  "w": 140.89,
                  "x": 252.09,
                  "y": 173.49
                  },
                  "id": "ab8035d0-61b8-4294-b348-085461555df8",
                  "name": "dog",
                  "slot_names": [
                     "my_slot"
                  ]
               }
            ]
         }
         """

        file_path.write_text(json)

        annotation_file: Optional[AnnotationFile] = parse_path(file_path)
        assert annotation_file is not None

        assert annotation_file.path == file_path
        assert annotation_file.filename == "my_image.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        for annotation in annotation_file.annotations:
            assert annotation.slot_names == ["my_slot"]

    def test_it_skips_slot_names_when_no_slot_names_for_sequences(file_path: Path):
        json: str = """
        {
         "dataset": "test",
         "image": {
            "width": 2479,
            "height": 3508,
            "fps": 30.0,
            "original_filename": "Invoice.pdf",
            "filename": "Invoice.pdf",
            "url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/1a46356d-005b-4095-98fc-fc4ea6d7294a/original",
            "path": "/",
            "workview_url": "https://staging.v7labs.com/teams/rafals-team/items/0182e9d2-d217-3260-52db-d7828422f86b/workview",
            "frame_count": 2,
            "frame_urls": [
               "https://staging.v7labs.com/api/v2/teams/rafals-team/files/1a46356d-005b-4095-98fc-fc4ea6d7294a/sections/0",
               "https://staging.v7labs.com/api/v2/teams/rafals-team/files/1a46356d-005b-4095-98fc-fc4ea6d7294a/sections/1"
            ]
         },
         "annotations": [
            {
               "frames": {
                  "0": {
                     "bounding_box": {
                        "h": 338.29,
                        "w": 444.87,
                        "x": 845.6,
                        "y": 1056.57
                     },
                     "keyframe": true,
                     "text": {
                        "text": "some weird text"
                     }
                  }
               },
               "id": "d89a5895-c721-420b-9c7d-d71880e3679b",
               "interpolate_algorithm": "linear-1.1",
               "interpolated": true,
               "name": "address",
               "segments": [
                  [0, 2]
               ]
            }
         ]
         }
        """

        file_path.write_text(json)

        annotation_file: Optional[AnnotationFile] = parse_path(file_path)
        assert annotation_file is not None

        assert annotation_file.path == file_path
        assert annotation_file.filename == "Invoice.pdf"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        for annotation in annotation_file.annotations:
            assert annotation.slot_names == []

    def test_it_skips_slot_names_when_no_slot_names_for_images(file_path: Path):
        json: str = """
         {
            "dataset": "test",
            "image": {
               "width": 500,
               "height": 375,
               "original_filename": "my_image.jpg",
               "filename": "my_image.jpg",
               "url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/d119a57f-bbbb-4b9b-a7a2-6dcb16a59e98/original",
               "thumbnail_url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/d119a57f-bbbb-4b9b-a7a2-6dcb16a59e98/thumbnail",
               "path": "/",
               "workview_url": "https://staging.v7labs.com/teams/rafals-team/items/0182e9d2-d217-681d-2448-197904d2e05c/workview"
            },
            "annotations": [
               {
                  "bounding_box": {
                  "h": 151.76,
                  "w": 140.89,
                  "x": 252.09,
                  "y": 173.49
                  },
                  "id": "ab8035d0-61b8-4294-b348-085461555df8",
                  "name": "dog"
               }
            ]
         }
         """

        file_path.write_text(json)

        annotation_file: Optional[AnnotationFile] = parse_path(file_path)
        assert annotation_file is not None

        assert annotation_file.path == file_path
        assert annotation_file.filename == "my_image.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        for annotation in annotation_file.annotations:
            assert annotation.slot_names == []
