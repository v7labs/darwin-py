from unittest.mock import MagicMock, patch

from darwin.utils import (
    is_extension_allowed,
    is_image_extension_allowed,
    is_project_dir,
    is_unix_like_os,
    is_video_extension_allowed,
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
