from pathlib import Path

from darwin.utils.utils import get_image_path_from_stream


class TestGetImagePathFromStream:
    def test_with_folders_true(self):
        darwin_json = {"item": {"name": "image.jpg", "path": "/folder"}}
        images_dir = Path("/images")
        annotation_filepath = Path("/annotations/annotation.json")
        expected = Path("/images/folder/image.jpg")
        result = get_image_path_from_stream(
            darwin_json, images_dir, annotation_filepath, True
        )
        assert result == expected

    def test_with_folders_false(self):
        darwin_json = {"item": {"name": "image.jpg", "path": "/folder"}}
        images_dir = Path("/images")
        annotation_filepath = Path("/annotations/annotation.json")
        expected = Path("/images/image.jpg")
        result = get_image_path_from_stream(
            darwin_json, images_dir, annotation_filepath, False
        )
        assert result == expected
