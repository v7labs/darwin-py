from unittest.mock import MagicMock, patch

import darwin.datatypes as dt
from darwin.utils import (
    is_extension_allowed,
    is_image_extension_allowed,
    is_project_dir,
    is_unix_like_os,
    is_video_extension_allowed,
    parse_darwin_json,
    urljoin,
)


def describe_is_extension_allowed():
    def it_returns_true_for_allowed_extensions():
        assert is_extension_allowed(".png")

    def it_returns_false_for_unknown_extensions():
        assert not is_extension_allowed(".mkv")


def describe_is_image_extension_allowed():
    def it_returns_true_for_allowed_extensions():
        assert is_image_extension_allowed(".png")

    def it_returns_false_for_unknown_extensions():
        assert not is_image_extension_allowed(".not_an_image")


def describe_is_video_extension_allowed():
    def it_returns_true_for_allowed_extensions():
        assert is_video_extension_allowed(".mp4")

    def it_returns_false_for_unknown_extensions():
        assert not is_video_extension_allowed(".not_video")


def describe_urljoin():
    def it_returns_an_url():
        assert urljoin("api", "teams") == "api/teams"

    def it_strips_correctly():
        assert (
            urljoin("http://www.darwin.v7labs.com/", "/users/token_info")
            == "http://www.darwin.v7labs.com/users/token_info"
        )


def describe_is_project_dir():
    def it_returns_true_if_path_is_project_dir(tmp_path):
        releases_path = tmp_path / "releases"
        releases_path.mkdir()

        images_path = tmp_path / "images"
        images_path.mkdir()

        assert is_project_dir(tmp_path)

    def it_returns_false_if_path_is_not_project_dir(tmp_path):
        assert not is_project_dir(tmp_path)


def describe_is_unix_like_os():
    @patch("platform.system", return_value="Linux")
    def it_returns_true_on_linux(mock: MagicMock):
        assert is_unix_like_os()
        mock.assert_called_once()

    @patch("platform.system", return_value="Windows")
    def it_returns_false_on_windows(mock: MagicMock):
        assert not is_unix_like_os()
        mock.assert_called_once()

    @patch("platform.system", return_value="Darwin")
    def it_returns_true_on_mac_os(mock: MagicMock):
        assert is_unix_like_os()
        mock.assert_called_once()


def describe_parse_darwin_json():
    def it_parses_darwin_images_correctly(tmp_path):
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

    def it_parses_darwin_videos_correctly(tmp_path):
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
        assert len(annotation_file.annotations) == 1
        assert len(annotation_file.annotation_classes) == 1
        assert annotation_file.is_video
        assert annotation_file.image_width == 3840
        assert annotation_file.image_height == 2160
        assert annotation_file.image_url == "https://my-website.com/api/videos/209/original"
        assert annotation_file.workview_url == "https://my-website.com/workview?dataset=102&image=530"
        assert not annotation_file.seq
        assert annotation_file.frame_urls == ["https://my-website.com/api/videos/209/frames/0"]
        assert annotation_file.remote_path == "/"

        assert annotation_file.annotations == [
            dt.VideoAnnotation(
                annotation_class=dt.AnnotationClass(
                    name="Hand", annotation_type="polygon", annotation_internal_type=None
                ),
                frames={
                    3: dt.Annotation(
                        annotation_class=dt.AnnotationClass(
                            name="Hand", annotation_type="polygon", annotation_internal_type=None
                        ),
                        data={
                            "path": [{"x": 748.0, "y": 732.0}, {"x": 751.0, "y": 735.0}, {"x": 748.0, "y": 733.0}],
                            "bounding_box": {"x": 363.0, "y": 701.0, "w": 400.0, "h": 547.0},
                        },
                        subs=[dt.SubAnnotation(annotation_type="instance_id", data=119)],
                    )
                },
                keyframes={3: True},
                segments=[[3, 46]],
                interpolated=True,
            )
        ]

    def it_returns_None_if_no_annotations_exist(tmp_path):
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

    def it_uses_a_default_path_if_one_is_missing(tmp_path):
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

    def it_imports_a_skeleton(tmp_path):
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

        assert annotation_file.annotations[0].annotation_class.annotation_type == "polygon"
        assert annotation_file.annotations[1].annotation_class.annotation_type == "skeleton"

    def it_imports_multiple_skeletetons(tmp_path):
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

        assert annotation_file.annotations[0].annotation_class.annotation_type == "polygon"
        assert annotation_file.annotations[1].annotation_class.annotation_type == "skeleton"
        assert annotation_file.annotations[2].annotation_class.annotation_type == "skeleton"

