from pathlib import Path
from typing import Optional

import pytest

from darwin.datatypes import AnnotationFile
from darwin.importer.formats.darwin import parse_path


class TestParsePath:
    @pytest.fixture
    def file_path(self, tmp_path: Path):
        path = tmp_path / "annotation.json"
        yield path
        path.unlink()

    def test_it_returns_none_if_there_are_no_annotations(self):
        path = Path("path/to/file.xml")
        assert parse_path(path) is None

    def test_it_parses_slot_names_properly_if_present_for_sequences(
        self, file_path: Path
    ):
        json: str = """
      {
      "version": "2.0",
      "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
      "item": {
         "name": "Invoice.pdf",
         "path": "/",
         "source_info": {
            "item_id": "018e3385-822c-fbab-e766-acd624a8a273",
            "dataset": {
            "name": "folder_test",
            "slug": "folder_test",
            "dataset_management_url": "https://darwin.v7labs.com/datasets/722603/dataset-management"
            },
            "team": {
            "name": "V7 John",
            "slug": "v7-john"
            },
            "workview_url": "https://darwin.v7labs.com/workview?dataset=722603&item=018e3385-822c-fbab-e766-acd624a8a273"
         },
         "slots": [
            {
            "type": "video",
            "slot_name": "0",
            "width": 1920,
            "height": 1080,
            "fps": 1,
            "thumbnail_url": "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/thumbnail",
            "source_files": [
               {
                  "file_name": "mini_uct.mp4",
                  "url": "https://darwin.v7labs.com/api/v2/teams/v7-john/uploads/db035ac4-4327-4b11-85b7-432c0e09c896"
               }
            ],
            "frame_count": 8,
            "frame_urls": [
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/0",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/1",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/2",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/3",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/4",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/5",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/6",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/7"
            ]
            }
         ]
      },
      "annotations": [
         {
            "frames": {
            "0": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": true
            },
            "1": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "2": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "3": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "4": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "5": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "6": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "7": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": true
            }
            },
            "hidden_areas": [],
            "id": "06865ac8-d2f8-4b8f-a653-9cd08df5b3f5",
            "interpolate_algorithm": "linear-1.1",
            "interpolated": true,
            "name": "curia",
            "properties": [],
            "ranges": [
            [
               0,
               8
            ]
            ],
            "slot_names": [
            "0"
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
            assert annotation.slot_names == ["0"]

    def test_it_parses_slot_names_properly_if_present_for_images(self, file_path: Path):
        json: str = """
         {
         "version": "2.0",
         "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
         "item": {
            "name": "ferrari-laferrari.jpg",
            "path": "/",
            "source_info": {
               "item_id": "018c4450-d91d-ff3e-b226-60d48b66f86e",
               "dataset": {
               "name": "bbox",
               "slug": "bbox",
               "dataset_management_url": "https://darwin.v7labs.com/datasets/623079/dataset-management"
               },
               "team": {
               "name": "V7 John",
               "slug": "v7-john"
               },
               "workview_url": "https://darwin.v7labs.com/workview?dataset=623079&item=018c4450-d91d-ff3e-b226-60d48b66f86e"
            },
            "slots": [
               {
               "type": "image",
               "slot_name": "0",
               "width": 640,
               "height": 425,
               "thumbnail_url": "https://darwin.v7labs.com/api/v2/teams/v7-john/files/ddc5cbc2-8438-4e36-8ab6-43e2f3746bf1/thumbnail",
               "source_files": [
                  {
                     "file_name": "000000007751.jpg",
                     "url": "https://darwin.v7labs.com/api/v2/teams/v7-john/uploads/3395d29a-7539-4a51-a3ca-c7a95f460345"
                  }
               ]
               }
            ]
         },
         "annotations": [
            {
               "bounding_box": {
               "h": 53.963699999999996,
               "w": 83.7195,
               "x": 32.7817,
               "y": 53.9638
               },
               "id": "8940a690-d8a9-4c83-9f59-38f0ef780246",
               "name": "new-class-2",
               "polygon": {
               "paths": [
                  [
                     {
                     "x": 65.0591,
                     "y": 53.9638
                     },
                     {
                     "x": 32.7817,
                     "y": 107.9275
                     },
                     {
                     "x": 116.5012,
                     "y": 104.9015
                     }
                  ]
               ]
               },
               "properties": [],
               "slot_names": [
               "0"
               ]
            },
            {
               "id": "782618fb-4c69-436e-80cb-71765d255dbf",
               "name": "skeleton-test",
               "properties": [],
               "skeleton": {
               "nodes": [
                  {
                     "name": "node",
                     "occluded": false,
                     "x": 264.7754,
                     "y": 121.5445
                  },
                  {
                     "name": "2",
                     "occluded": false,
                     "x": 245.1335,
                     "y": 107.3425
                  },
                  {
                     "name": "3",
                     "occluded": false,
                     "x": 240.4646,
                     "y": 125.4178
                  },
                  {
                     "name": "4",
                     "occluded": false,
                     "x": 280.3923,
                     "y": 137.468
                  }
               ]
               },
               "slot_names": [
               "0"
               ]
            },
            {
               "id": "b6bea00c-c8a4-4d34-b72f-88567d9e8cd5",
               "name": "skeleton-test",
               "properties": [],
               "skeleton": {
               "nodes": [
                  {
                     "name": "node",
                     "occluded": false,
                     "x": 136.1702,
                     "y": 306.1308
                  },
                  {
                     "name": "2",
                     "occluded": false,
                     "x": 145.1629,
                     "y": 291.263
                  },
                  {
                     "name": "3",
                     "occluded": false,
                     "x": 147.3005,
                     "y": 310.1857
                  },
                  {
                     "name": "4",
                     "occluded": false,
                     "x": 129.0203,
                     "y": 322.8007
                  }
               ]
               },
               "slot_names": [
               "0"
               ]
            }
         ]
         }
         """

        file_path.write_text(json)

        annotation_file: Optional[AnnotationFile] = parse_path(file_path)
        assert annotation_file is not None

        assert annotation_file.path == file_path
        assert annotation_file.filename == "ferrari-laferrari.jpg"
        assert annotation_file.annotation_classes
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations

        for annotation in annotation_file.annotations:
            assert annotation.slot_names == ["0"]

    def test_it_skips_slot_names_when_no_slot_names_for_sequences(
        self, file_path: Path
    ):
        json: str = """
      {
      "version": "2.0",
      "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
      "item": {
         "name": "Invoice.pdf",
         "path": "/",
         "source_info": {
            "item_id": "018e3385-822c-fbab-e766-acd624a8a273",
            "dataset": {
            "name": "folder_test",
            "slug": "folder_test",
            "dataset_management_url": "https://darwin.v7labs.com/datasets/722603/dataset-management"
            },
            "team": {
            "name": "V7 John",
            "slug": "v7-john"
            },
            "workview_url": "https://darwin.v7labs.com/workview?dataset=722603&item=018e3385-822c-fbab-e766-acd624a8a273"
         },
         "slots": [
            {
            "type": "video",
            "slot_name": "",
            "width": 1920,
            "height": 1080,
            "fps": 1,
            "thumbnail_url": "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/thumbnail",
            "source_files": [
               {
                  "file_name": "mini_uct.mp4",
                  "url": "https://darwin.v7labs.com/api/v2/teams/v7-john/uploads/db035ac4-4327-4b11-85b7-432c0e09c896"
               }
            ],
            "frame_count": 8,
            "frame_urls": [
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/0",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/1",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/2",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/3",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/4",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/5",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/6",
               "https://darwin.v7labs.com/api/v2/teams/v7-john/files/926ee041-03c0-4354-aea2-8b9db422341d/sections/7"
            ]
            }
         ]
      },
      "annotations": [
         {
            "frames": {
            "0": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": true
            },
            "1": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "2": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "3": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "4": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "5": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "6": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": false
            },
            "7": {
               "bounding_box": {
                  "h": 152.502,
                  "w": 309.579,
                  "x": 466.6561,
                  "y": 338.5544
               },
               "keyframe": true
            }
            },
            "hidden_areas": [],
            "id": "06865ac8-d2f8-4b8f-a653-9cd08df5b3f5",
            "interpolate_algorithm": "linear-1.1",
            "interpolated": true,
            "name": "curia",
            "properties": [],
            "ranges": [
            [
               0,
               8
            ]
            ],
            "slot_names": []
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

    def test_it_skips_slot_names_when_no_slot_names_for_images(self, file_path: Path):
        json: str = """
         {
         "version": "2.0",
         "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
         "item": {
            "name": "my_image.jpg",
            "path": "/",
            "source_info": {
               "item_id": "0182e9d2-d217-681d-2448-197904d2e05c",
               "dataset": {
               "name": "test",
               "slug": "test",
               "dataset_management_url": "https://staging.v7labs.com/teams/rafals-team/items/0182e9d2-d217-681d-2448-197904d2e05c/workview"
               },
               "team": {
               "name": "rafals-team",
               "slug": "rafals-team"
               },
               "workview_url": "https://staging.v7labs.com/teams/rafals-team/items/0182e9d2-d217-681d-2448-197904d2e05c/workview"
            },
            "slots": [
               {
               "type": "image",
               "slot_name": "",
               "width": 500,
               "height": 375,
               "thumbnail_url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/d119a57f-bbbb-4b9b-a7a2-6dcb16a59e98/thumbnail",
               "source_files": [
                  {
                     "file_name": "my_image.jpg",
                     "url": "https://staging.v7labs.com/api/v2/teams/rafals-team/files/d119a57f-bbbb-4b9b-a7a2-6dcb16a59e98/original"
                  }
               ]
               }
            ]
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
               "properties": [],
               "slot_names": []
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
