from unittest.mock import MagicMock, patch

import pytest
from jsonschema.exceptions import ValidationError
from requests import Response

import darwin.datatypes as dt
import darwin.exceptions as de
from darwin.utils import (
    get_response_content,
    has_json_content_type,
    is_extension_allowed,
    is_image_extension_allowed,
    is_project_dir,
    is_unix_like_os,
    is_video_extension_allowed,
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
    def test_returns_true_for_allowed_extensions(self):
        assert is_extension_allowed(".png")

    def test_returns_false_for_unknown_extensions(self):
        assert not is_extension_allowed(".mkv")

    def test_returns_true_for_allowed_image_extensions(self):
        assert is_image_extension_allowed(".png")

    def test_returns_false_for_unknown_image_extensions(self):
        assert not is_image_extension_allowed(".not_an_image")

    def test_returns_true_for_allowed_video_extensions(self):
        assert is_video_extension_allowed(".mp4")

    def test_returns_false_for_unknown_video_extensions(self):
        assert not is_video_extension_allowed(".not_video")


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
            "image": {
                "width": 497,
                "height": 778,
                "original_filename": "P49-RediPad-ProPlayLEFTY_442.jpg",
                "filename": "P49-RediPad-ProPlayLEFTY_442.jpg",
                "url": "",
                "path": "/tmp_files"
            },
            "annotations": [
                {
                    "keypoint": {
                        "x": 207.97048950195312,
                        "y": 449.39691162109375
                    },
                    "name": "left_knee"
                },
                {
                    "keypoint": {
                        "x": 302.9606018066406,
                        "y": 426.13946533203125
                    },
                    "name": "left_ankle"
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
        assert annotation_file.dataset_name == None
        assert annotation_file.version == dt.AnnotationFileVersion(
            major=1, minor=0, suffix=""
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
            "dataset": "my-dataset",
            "image": {
                "width": 3840,
                "height": 2160,
                "fps": 0.0,
                "original_filename": "above tractor.mp4",
                "filename": "above tractor.mp4",
                "url": "https://my-website.com/api/videos/209/original",
                "path": "/",
                "workview_url": "https://my-website.com/workview?dataset=102&image=530",
                "frame_count": 343,
                "frame_urls": [
                "https://my-website.com/api/videos/209/frames/0"
                ]
            },
            "annotations": [
                {
                    "frames": {
                        "3": {
                            "bounding_box": {
                                "h": 547.0,
                                "w": 400.0,
                                "x": 363.0,
                                "y": 701.0
                            },
                            "instance_id": {
                                "value": 119
                            },
                            "keyframe": true,
                            "polygon": {
                                "path": [
                                    {
                                        "x": 748.0,
                                        "y": 732.0
                                    },
                                    {
                                        "x": 751.0,
                                        "y": 735.0
                                    },
                                    {
                                        "x": 748.0,
                                        "y": 733.0
                                    }
                                ]
                            }
                        }
                    },
                    "interpolate_algorithm": "linear-1.1",
                    "interpolated": true,
                    "name": "Hand",
                    "segments": [
                        [
                            3,
                            46
                        ]
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
        assert annotation_file.filename == "above tractor.mp4"
        assert annotation_file.dataset_name == None
        assert annotation_file.version == dt.AnnotationFileVersion(
            major=1, minor=0, suffix=""
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
                    annotation_internal_type=None,
                ),
                frames={
                    3: dt.Annotation(
                        annotation_class=dt.AnnotationClass(
                            name="Hand",
                            annotation_type="polygon",
                            annotation_internal_type=None,
                        ),
                        data={
                            "path": [
                                {"x": 748.0, "y": 732.0},
                                {"x": 751.0, "y": 735.0},
                                {"x": 748.0, "y": 733.0},
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
                    )
                },
                keyframes={3: True},
                segments=[[3, 46]],
                interpolated=True,
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
                "image": {
                    "original_filename": "P49-RediPad-ProPlayLEFTY_442.jpg",
                    "filename": "P49-RediPad-ProPlayLEFTY_442.jpg"
                },
                "annotations": [
                    {
                        "keypoint": {
                            "x": 207.97048950195312,
                            "y": 449.39691162109375
                        },
                        "name": "left_knee"
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
                "dataset": "cars",
                "image": {
                    "filename": "ferrari-laferrari.jpg"
                },
                "annotations": [
                    {
                        "bounding_box": {
                            "h": 547.0,
                            "w": 1709.0,
                            "x": 96.0,
                            "y": 437.0
                        },
                        "name": "car",
                        "polygon": {
                            "path": [
                                {
                                    "x": 1805.0,
                                    "y": 586.0
                                },
                                {
                                    "x": 1802.0,
                                    "y": 586.0
                                },
                                {
                                    "x": 1805.0,
                                    "y": 588.0
                                }
                            ]
                        }
                    },
                    {
                        "name": "wheels",
                        "skeleton": {
                            "nodes": [
                                {
                                    "name": "1",
                                    "occluded": false,
                                    "x": 829.56,
                                    "y": 824.5
                                },
                                {
                                    "name": "2",
                                    "occluded": false,
                                    "x": 1670.5,
                                    "y": 741.76
                                }
                            ]
                        }
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
                "dataset":"cars",
                "image":{
                    "filename":"ferrari-laferrari.jpg"
                },
                "annotations":[
                    {
                        "bounding_box":{
                            "h":547.0,
                            "w":1709.0,
                            "x":96.0,
                            "y":437.0
                        },
                        "name":"car",
                        "polygon":{
                            "path":[
                                {
                                    "x":1805.0,
                                    "y":586.0
                                },
                                {
                                    "x":1802.0,
                                    "y":586.0
                                },
                                {
                                    "x":1805.0,
                                    "y":588.0
                                }
                            ]
                        }
                    },
                    {
                        "name":"wheels",
                        "skeleton":{
                            "nodes":[
                                {
                                    "name":"1",
                                    "occluded":false,
                                    "x":829.56,
                                    "y":824.5
                                },
                                {
                                    "name":"2",
                                    "occluded":false,
                                    "x":1670.5,
                                    "y":741.76
                                }
                            ]
                        }
                    },
                    {
                        "name":"door",
                        "skeleton":{
                            "nodes":[
                                {
                                    "name":"1",
                                    "occluded":false,
                                    "x":867.86,
                                    "y":637.16
                                },
                                {
                                    "name":"2",
                                    "occluded":false,
                                    "x":1100.21,
                                    "y":810.09
                                },
                                {
                                    "name":"3",
                                    "occluded":false,
                                    "x":1298.45,
                                    "y":856.56
                                },
                                {
                                    "name":"4",
                                    "occluded":false,
                                    "x":1234.63,
                                    "y":492.12
                                }
                            ]
                        }
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

        assert annotation.data["sparse_rle"] == None

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
