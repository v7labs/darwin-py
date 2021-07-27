from darwin.utils import is_unix_like_os


def describe_is_unix_like_os():
    def it_returns_true_for_unix_like_os():
        assert is_unix_like_os()
