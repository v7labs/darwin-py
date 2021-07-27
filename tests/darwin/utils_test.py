from unittest.mock import MagicMock, patch

from darwin.utils import is_unix_like_os


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
