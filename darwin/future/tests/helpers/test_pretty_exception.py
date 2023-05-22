import sys
from contextlib import _GeneratorContextManager, contextmanager
from unittest.mock import MagicMock, patch

import pytest
from pytest import CaptureFixture

from darwin.future.exceptions.base import DarwinException
from darwin.future.helpers.pretty_exception import PrettyExceptionMode, pretty_exception

CapsysType = CaptureFixture[str]


def throws_exception() -> _GeneratorContextManager[None]:
    raise DarwinException("Test exception")


def test_pretty_exception_raise(capsys: CapsysType) -> None:
    with pytest.raises(DarwinException):
        with throws_exception():
            pretty_exception(mode=PrettyExceptionMode.RAISE)
            captured = capsys.readouterr()
            assert "Unknown error occurred." in captured.out


def test_pretty_exception_with_exception(capsys: CapsysType) -> None:
    with pytest.raises(DarwinException):
        with throws_exception():
            pretty_exception(mode=PrettyExceptionMode.RAISE)
            captured = capsys.readouterr()
            assert "Test exception" in captured.out


def test_pretty_exception_with_exception_frame_limit(capsys: CapsysType) -> None:
    with pytest.raises(DarwinException):
        with throws_exception():
            pretty_exception(mode=PrettyExceptionMode.RAISE, frame_limit=3)
            captured = capsys.readouterr()
            assert "Test exception" in captured.out
            assert captured.out.count("File") <= 3  # type: ignore
