from unittest.mock import MagicMock, patch

import pytest
from requests import Response

import darwin.datatypes as dt
import darwin.exceptions as de
from darwin.utils import (
    get_response_content,
    has_json_content_type,
    is_image_extension_allowed,
    is_project_dir,
    is_unix_like_os,
    parse_darwin_json,
    urljoin,
    validate_data_against_schema,
)
from darwin.utils.utils import (
    _parse_darwin_mask_annotation,
    _parse_darwin_raster_annotation,
)


class TestValidation:
    def test_should_raise_missing_schema_url(self):
        with pytest.raises(de.MissingSchema) as error:
            validate_data_against_schema({})
        assert "Schema not found" in str(error.value)

    def test_fails_on_incorrect_data(self):
        data = {
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json_2_0.schema.json",
        }
        assert len(validate_data_against_schema(data)) >= 1

    def test_validates_correct_data(self):
        data = {
            "version": "2.0",
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json_2_0.schema.json",
            "item": {"name": "", "path": ""},
            "annotations": [],
        }
        assert len(validate_data_against_schema(data)) == 0


class TestExtensions:
    def test_returns_true_for_allowed_image_extensions(self):
        assert is_image_extension_allowed(".png")

    def test_returns_false_for_unknown_image_extensions(self):
        assert not is_image_extension_allowed(".not_an_image")


class TestUrlJoin:
    def test_returns_an_url(self):
        assert urljoin("api", "teams") == "api/teams"

    def test_strips_correctly(self):
        assert (
            urljoin("http://www.darwin.v7labs.com/", "/users/token_info")
            == "http://www.darwin.v7labs.com/users/token_info"
        )


class TestProjectDir:
    def test_returns_true_if_path_is_project_dir(self, tmp_path):
        releases_path = tmp_path / "releases"
        releases_path.mkdir()

        images_path = tmp_path / "images"
        images_path.mkdir()

        assert is_project_dir(tmp_path)

    def test_returns_false_if_path_is_not_project_dir(self, tmp_path):
        assert not is_project_dir(tmp_path)


class TestUnixLikeOS:
    @patch("platform.system", return_value="Linux")
    def test_returns_true_on_linux(self, mock: MagicMock):
        assert is_unix_like_os()
        mock.assert_called_once()

    @patch("platform.system", return_value="Windows")
    def test_returns_false_on_windows(self, mock: MagicMock):
        assert not is_unix_like_os()
        mock.assert_called_once()

    @patch("platform.system", return_value="Darwin")
    def test_returns_true_on_mac_os(self, mock: MagicMock):
        assert is_unix_like_os()
        mock.assert_called_once()


class TestParseDarwinJson:
    def test_parses_darwin_images_correctly(self, tmp_path):
        content = """
        {
            "version": "2.0",
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
            "item": {
                "name": "P49-RediPad-ProPlayLEFTY_442.jpg",
                "path": "/tmp_files",
                "slots": [
                {
                    "type": "image",
                    "slot_name": "0",
                    "width": 497,
                    "height": 778,
                    "source_files": [
                    {
                        "file_name": "P49-RediPad-ProPlayLEFTY_442.jpg",
                        "url": ""
                    }
                    ]
                }
                ]
            },
            "annotations": [
                {
                "id": "unique_id_1",
                "name": "left_knee",
                "keypoint": {
                    "x": 207.97048950195312,
                    "y": 449.39691162109375
                },
                "slot_names": [
                    "0"
                ]
                },
                {
                "id": "unique_id_2",
                "name": "left_ankle",
                "keypoint": {
                    "x": 302.9606018066406,
                    "y": 426.13946533203125
                },
                "slot_names": [
                    "0"
                ]
                }
            ]
            }
        """

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert annotation_file.path == import_file
        assert annotation_file.filename == "P49-RediPad-ProPlayLEFTY_442.jpg"
        assert annotation_file.dataset_name is None
        assert annotation_file.version == dt.AnnotationFileVersion(
            major=2, minor=0, suffix=""
        )

        assert len(annotation_file.annotations) == 2
        assert len(annotation_file.annotation_classes) == 2
        assert not annotation_file.is_video
        assert annotation_file.image_width == 497
        assert annotation_file.image_height == 778
        assert annotation_file.image_url == ""
        assert not annotation_file.workview_url
        assert not annotation_file.seq
        assert not annotation_file.frame_urls
        assert annotation_file.remote_path == "/tmp_files"

    def test_parses_darwin_videos_correctly(self, tmp_path):
        content = """
        {
            "version": "2.0",
            "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json_2_0.schema.json",
            "item": {
                "name": "above tractor.mp4",
                "path": "/",
                "source_info": {
                    "item_id": "018a4ad2-41cb-5b6a-8141-fe1afeb65746",
                    "team": {"name": "Test Team", "slug": "test-team"},
                    "dataset": {
                        "name": "My dataset",
                        "slug": "my-dataset",
                        "dataset_management_url": "https://my-website.com/datasets/018a4ad2-41cb-5b6a-8141-fe1afeb65746/dataset-management"
                    },
                    "workview_url": "https://my-website.com/workview?dataset=102&image=530"
                },
                "slots": [
                    {
                        "type": "video",
                        "slot_name": "0",
                        "width": 3840,
                        "height": 2160,
                        "fps": 0.0,
                        "thumbnail_url": "https://my-website.com/api/videos/209/thumbnail",
                        "source_files": [
                            {
                                "file_name": "above tractor.mp4",
                                "url": "https://my-website.com/api/videos/209/original"
                            }
                        ],
                        "frame_count": 343,
                        "frame_urls": ["https://my-website.com/api/videos/209/frames/0"]
                    }
                ]
            },
            "annotations": [
                {
                    "frames": {
                        "3": {
                            "bounding_box": {"h": 547.0, "w": 400.0, "x": 363.0, "y": 701.0},
                            "instance_id": {"value": 119},
                            "keyframe": true,
                            "polygon": {
                                "paths": [
                                    [
                                        {"x": 748.0, "y": 732.0},
                                        {"x": 751.0, "y": 735.0},
                                        {"x": 748.0, "y": 733.0}
                                    ]
                                ]
                            }
                        }
                    },
                    "id": "f8f5f235-bd47-47be-b4fe-07d49e0177a7",
                    "interpolate_algorithm": "linear-1.1",
                    "interpolated": true,
                    "name": "Hand",
                    "ranges": [[3, 46]],
                    "hidden_areas": [[5, 8]],
                    "slot_names": ["0"]
                }
            ]
        }
        """

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file)

        assert annotation_file.path == import_file
        assert annotation_file.filename == "above tractor.mp4"
        assert annotation_file.dataset_name == "My dataset"
        assert annotation_file.version == dt.AnnotationFileVersion(
            major=2, minor=0, suffix=""
        )

        assert len(annotation_file.annotations) == 1
        assert len(annotation_file.annotation_classes) == 1
        assert annotation_file.is_video
        assert annotation_file.image_width == 3840
        assert annotation_file.image_height == 2160
        assert (
            annotation_file.image_url
            == "https://my-website.com/api/videos/209/original"
        )
        assert (
            annotation_file.workview_url
            == "https://my-website.com/workview?dataset=102&image=530"
        )
        assert not annotation_file.seq
        assert annotation_file.frame_urls == [
            "https://my-website.com/api/videos/209/frames/0"
        ]
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations == [
            dt.VideoAnnotation(
                annotation_class=dt.AnnotationClass(
                    name="Hand",
                    annotation_type="polygon",
                    annotation_internal_type="polygon",
                ),
                frames={
                    3: dt.Annotation(
                        annotation_class=dt.AnnotationClass(
                            name="Hand",
                            annotation_type="polygon",
                            annotation_internal_type="polygon",
                        ),
                        data={
                            "paths": [
                                [
                                    {"x": 748.0, "y": 732.0},
                                    {"x": 751.0, "y": 735.0},
                                    {"x": 748.0, "y": 733.0},
                                ]
                            ],
                            "bounding_box": {
                                "x": 363.0,
                                "y": 701.0,
                                "w": 400.0,
                                "h": 547.0,
                            },
                        },
                        subs=[
                            dt.SubAnnotation(annotation_type="instance_id", data=119)
                        ],
                        slot_names=[],
                        annotators=None,
                        reviewers=None,
                        id="f8f5f235-bd47-47be-b4fe-07d49e0177a7",
                        properties=None,
                    )
                },
                keyframes={3: True},
                segments=[[3, 46]],
                hidden_areas=[[5, 8]],
                interpolated=True,
                slot_names=["0"],
                annotators=None,
                reviewers=None,
                id="f8f5f235-bd47-47be-b4fe-07d49e0177a7",
                properties=None,
            )
        ]

    def test_parses_darwin_v2_images_correctly(self, tmp_path):
        content = """
        {
          "version": "2.0",
          "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json_2_0.schema.json",
          "item": {
            "name": "item-0.jpg",
            "path": "/path-0/folder",
            "source_info": {
              "dataset": {
                "name": "Dataset 0",
                "slug": "dataset-0",
                "dataset_management_url": "http://example.com/datasets/545/dataset-management"
              },
              "item_id": "0185c280-bbad-6117-71a7-a6853a6e3f2e",
              "team": {
                "name": "Team 0",
                "slug": "team-0"
              },
              "workview_url": "http://example.com/workview?dataset=545&item=0185c280-bbad-6117-71a7-a6853a6e3f2e"
            },
            "slots": [
              {
                "type": "image",
                "slot_name": "0",
                "width": 123,
                "height": 456,
                "thumbnail_url": "http://example.com/fake-api-url/v2/teams/v7/files/71857eb3-6feb-428a-8fc6-0c8a895ea611/thumbnail",
                "source_files": [
                  {
                    "file_name": "file-0",
                    "url": "http://example.com/fake-api-url/v2/teams/v7/uploads/43a83276-1abf-483b-877e-6e61349f2d1f"
                  }
                ]
              }
            ]
          },
          "annotations": [
            {
              "bounding_box": {
                "h": 2,
                "w": 1,
                "x": 1,
                "y": 1
              },
              "id": "f8f5f235-bd47-47be-b4fe-07d49e0177a7",
              "name": "polygon",
              "polygon": {
                "paths": [
                  [
                    {
                      "x": 1,
                      "y": 1
                    },
                    {
                      "x": 2,
                      "y": 2
                    },
                    {
                      "x": 1,
                      "y": 3
                    }
                  ]
                ]
              },
              "slot_names": [
                "0"
              ]
            }
          ]
        }
        """

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert annotation_file.path == import_file
        assert annotation_file.filename == "item-0.jpg"
        assert annotation_file.dataset_name == "Dataset 0"
        assert annotation_file.item_id == "0185c280-bbad-6117-71a7-a6853a6e3f2e"
        assert annotation_file.version == dt.AnnotationFileVersion(
            major=2, minor=0, suffix=""
        )

        assert len(annotation_file.annotations) == 1
        assert len(annotation_file.annotation_classes) == 1
        assert (
            annotation_file.annotations[0].id == "f8f5f235-bd47-47be-b4fe-07d49e0177a7"
        )
        assert not annotation_file.is_video
        assert annotation_file.image_width == 123
        assert annotation_file.image_height == 456
        assert (
            annotation_file.image_url
            == "http://example.com/fake-api-url/v2/teams/v7/uploads/43a83276-1abf-483b-877e-6e61349f2d1f"
        )
        assert (
            annotation_file.workview_url
            == "http://example.com/workview?dataset=545&item=0185c280-bbad-6117-71a7-a6853a6e3f2e"
        )
        assert not annotation_file.seq
        assert not annotation_file.frame_urls
        assert annotation_file.remote_path == "/path-0/folder"

    def test_parses_darwin_v2_videos_correctly(self, tmp_path):
        content = """
        {
          "version": "2.0",
          "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json_2_0.schema.json",
          "item": {
            "name": "item-0.mp4",
            "path": "/path-0/folder",
            "source_info": {
              "dataset": {
                "name": "Dataset 0",
                "slug": "dataset-0",
                "dataset_management_url": "http://example.com/datasets/545/dataset-management"
              },
              "item_id": "0185c280-bbad-6117-71a7-a6853a6e3f2e",
              "team": {
                "name": "Team 0",
                "slug": "team-0"
              },
              "workview_url": "http://example.com/workview?dataset=545&item=0185c280-bbad-6117-71a7-a6853a6e3f2e"
            },
            "slots": [
              {
                "type": "video",
                "slot_name": "0",
                "width": 123,
                "height": 456,
                "thumbnail_url": "http://example.com/fake-api-url/v2/teams/v7/files/71857eb3-6feb-428a-8fc6-0c8a895ea611/thumbnail",
                "frame_urls": [
                  "http://example.com/fake-api-url/v2/teams/v7/files/71857eb3-6feb-428a-8fc6-0c8a895ea611/frames/1",
                  "http://example.com/fake-api-url/v2/teams/v7/files/71857eb3-6feb-428a-8fc6-0c8a895ea611/frames/2"
                ],
                "frame_count": 2,
                "source_files": [
                  {
                    "file_name": "file-0",
                    "url": "http://example.com/fake-api-url/v2/teams/v7/uploads/43a83276-1abf-483b-877e-6e61349f2d1f"
                  }
                ]
              }
            ]
          },
          "annotations": [
            {
              "frames": {
                "3": {
                  "bounding_box": {
                    "h": 2,
                    "w": 1,
                    "x": 1,
                    "y": 1
                  },
                  "polygon": {
                    "paths": [
                      [
                        { "x": 1, "y": 1 },
                        { "x": 2, "y": 2 },
                        { "x": 1, "y": 3 }
                      ]
                    ]
                  }
                }
              },
              "id": "f8f5f235-bd47-47be-b4fe-07d49e0177a7",
              "interpolate_algorithm": "linear-1.1",
              "interpolated": true,
              "name": "polygon",
              "ranges": [ [ 0, 1 ] ],
              "slot_names": [
                "1"
              ]
            }
          ]
        }
        """

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert annotation_file.path == import_file
        assert annotation_file.filename == "item-0.mp4"
        assert annotation_file.dataset_name == "Dataset 0"
        assert annotation_file.item_id == "0185c280-bbad-6117-71a7-a6853a6e3f2e"
        assert annotation_file.version == dt.AnnotationFileVersion(
            major=2, minor=0, suffix=""
        )

        assert len(annotation_file.annotations) == 1
        assert len(annotation_file.annotation_classes) == 1
        assert (
            annotation_file.annotations[0].id == "f8f5f235-bd47-47be-b4fe-07d49e0177a7"
        )
        assert list(annotation_file.annotations[0].frames.keys()) == [3]
        assert (
            annotation_file.annotations[0].frames[3].id
            == "f8f5f235-bd47-47be-b4fe-07d49e0177a7"
        )
        assert annotation_file.is_video
        assert annotation_file.image_width == 123
        assert annotation_file.image_height == 456
        assert (
            annotation_file.image_url
            == "http://example.com/fake-api-url/v2/teams/v7/uploads/43a83276-1abf-483b-877e-6e61349f2d1f"
        )
        assert (
            annotation_file.workview_url
            == "http://example.com/workview?dataset=545&item=0185c280-bbad-6117-71a7-a6853a6e3f2e"
        )
        assert not annotation_file.seq
        assert len(annotation_file.frame_urls) == 2
        assert annotation_file.remote_path == "/path-0/folder"

    def test_returns_None_if_no_annotations_exist(self, tmp_path):
        content = """
        {
            "image": {
                "width": 497,
                "height": 778,
                "original_filename": "P49-RediPad-ProPlayLEFTY_442.jpg",
                "filename": "P49-RediPad-ProPlayLEFTY_442.jpg",
                "url": "",
                "path": "/tmp_files"
            }
        }
        """

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert not annotation_file

    def test_uses_a_default_path_if_one_is_missing(self, tmp_path):
        content = """
        {
        "version": "2.0",
        "schema_ref": "https://darwin-public.s3.eu-west-1.amazonaws.com/darwin_json/2.0/schema.json",
        "item": {
            "name": "P49-RediPad-ProPlayLEFTY_442.jpg",
            "path": "/",
            "source_info": {
            "item_id": "unknown",
            "dataset": {
                "name": "unknown",
                "slug": "unknown",
                "dataset_management_url": "unknown"
            },
            "team": {
                "name": "unknown",
                "slug": "unknown"
            },
            "workview_url": "unknown"
            },
            "slots": [
            {
                "type": "image",
                "slot_name": "0",
                "width": 640,
                "height": 425,
                "thumbnail_url": "unknown",
                "source_files": [
                {
                    "file_name": "P49-RediPad-ProPlayLEFTY_442.jpg",
                    "url": "unknown"
                }
                ]
            }
            ]
        },
        "annotations": [
            {
            "id": "unknown",
            "name": "left_knee",
            "properties": [],
            "keypoint": {
                "x": 207.97048950195312,
                "y": 449.39691162109375
            },
            "slot_names": [
                "0"
            ]
            }
        ]
        }
            """

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert annotation_file.remote_path == "/"

    def test_imports_a_skeleton(self, tmp_path):
        content = """
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

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert (
            annotation_file.annotations[0].annotation_class.annotation_type == "polygon"
        )
        assert (
            annotation_file.annotations[1].annotation_class.annotation_type
            == "skeleton"
        )

    def test_imports_multiple_skeletetons(self, tmp_path):
        content = """
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

        directory = tmp_path / "imports"
        directory.mkdir()
        import_file = directory / "darwin-file.json"
        import_file.write_text(content)

        annotation_file: dt.AnnotationFile = parse_darwin_json(import_file, None)

        assert (
            annotation_file.annotations[0].annotation_class.annotation_type == "polygon"
        )
        assert (
            annotation_file.annotations[1].annotation_class.annotation_type
            == "skeleton"
        )
        assert (
            annotation_file.annotations[2].annotation_class.annotation_type
            == "skeleton"
        )

    def test_returns_true_w_json_content_type(self):
        response: Response = Response()
        response.headers["content-type"] = "application/json"
        assert has_json_content_type(response)

    def test_returns_false_w_plain_text(self):
        response: Response = Response()
        response.headers["content-type"] = "text/plain"
        assert not has_json_content_type(response)

    def test_returns_json_w_json_response(self):
        response: Response = Response()
        response.headers["content-type"] = "application/json"
        response._content = b'{"key":"a"}'
        assert {"key": "a"} == get_response_content(response)

    def test_returns_text_w_plain_text(self):
        response: Response = Response()
        response.headers["content-type"] = "text/plain"
        response._content = b"hello"
        assert "hello" == get_response_content(response)


class TestParseDarwinRasterAnnotation:
    @pytest.fixture
    def good_raster_annotation(self) -> dt.JSONFreeForm:
        return {
            "id": "abc123",
            "name": "my_raster_annotation",
            "raster_layer": {
                "dense_rle": "ABCD",
                "mask_annotation_ids_mapping": {"1": 1},
                "total_pixels": 100,
            },
            "slot_names": ["0"],
        }

    def test_parses_a_raster_annotation(
        self, good_raster_annotation: dt.JSONFreeForm
    ) -> None:
        annotation = _parse_darwin_raster_annotation(good_raster_annotation)

        assert annotation is not None
        assert annotation.annotation_class is not None

        assert annotation.annotation_class.name == "my_raster_annotation"
        assert annotation.annotation_class.annotation_type == "raster_layer"

        assert annotation.data["dense_rle"] == "ABCD"
        assert annotation.data["mask_annotation_ids_mapping"] == {"1": 1}
        assert annotation.data["total_pixels"] == 100
        assert annotation.id == "abc123"

    # Sad paths
    @pytest.mark.parametrize("parameter_name", ["id", "name", "raster_layer"])
    def test_raises_value_error_for_missing_top_level_fields(
        self, good_raster_annotation: dt.JSONFreeForm, parameter_name: str
    ) -> None:
        annotation = good_raster_annotation
        del annotation[parameter_name]
        with pytest.raises(ValueError):
            _parse_darwin_raster_annotation(annotation)

    @pytest.mark.parametrize(
        "parameter_name", ["dense_rle", "mask_annotation_ids_mapping", "total_pixels"]
    )
    def test_raises_value_error_for_missing_raster_layer_fields(
        self, good_raster_annotation: dt.JSONFreeForm, parameter_name: str
    ) -> None:
        annotation = good_raster_annotation
        del annotation["raster_layer"][parameter_name]
        with pytest.raises(ValueError):
            _parse_darwin_raster_annotation(annotation)


class TestParseDarwinMaskAnnotation:
    @pytest.fixture
    def good_mask_annotation(self) -> dt.JSONFreeForm:
        return {
            "id": "abc123",
            "name": "my_raster_annotation",
            "mask": {
                "sparse_rle": None,
            },
            "slot_names": ["0"],
        }

    def test_parses_a_raster_annotation(
        self, good_mask_annotation: dt.JSONFreeForm
    ) -> None:
        annotation = _parse_darwin_mask_annotation(good_mask_annotation)

        assert annotation is not None
        assert annotation.annotation_class is not None

        assert annotation.annotation_class.name == "my_raster_annotation"
        assert annotation.annotation_class.annotation_type == "mask"

        assert annotation.data["sparse_rle"] is None

    # Sad paths
    @pytest.mark.parametrize("parameter_name", ["id", "name", "mask", "slot_names"])
    def test_raises_value_error_for_missing_top_level_fields(
        self, good_mask_annotation: dt.JSONFreeForm, parameter_name: str
    ) -> None:
        annotation = good_mask_annotation
        del annotation[parameter_name]
        with pytest.raises(ValueError):
            _parse_darwin_raster_annotation(annotation)

    def test_raises_value_error_for_missing_mask_fields(
        self, good_mask_annotation: dt.JSONFreeForm
    ) -> None:
        annotation = good_mask_annotation
        del annotation["mask"]["sparse_rle"]
        with pytest.raises(ValueError):
            _parse_darwin_raster_annotation(annotation)

    def test_raises_value_error_for_invalid_mask_fields(
        self, good_mask_annotation: dt.JSONFreeForm
    ) -> None:
        annotation = good_mask_annotation
        annotation["mask"]["sparse_rle"] = "invalid"
        with pytest.raises(ValueError):
            _parse_darwin_raster_annotation(annotation)
