import sys
from enum import Enum, auto

from rich.console import Console

from darwin.future.exceptions.base import DarwinException


class PrettyExceptionMode(Enum):
    """
    An enum representing the different modes of pretty_exception.
    """

    HALT = auto()
    RAISE = auto()

    NEITHER_HALT_NOT_RAISE = auto()


def pretty_exception(mode: PrettyExceptionMode = PrettyExceptionMode.RAISE, frame_limit: int = 0) -> None:
    """
    Prints a formatted exception to the console, and optionally halts execution.

    Parameters
    ----------
    exception: Exception
        The exception to print.
    halt: bool
        Whether to halt execution after printing the exception.
    bubble: bool
        Whether to raise the exception after printing it.
    """
    exception = sys.last_value
    console = Console()

    console.print_exception(
        max_frames=frame_limit,
    )

    if mode == PrettyExceptionMode.HALT:
        console.print("Halting execution due to exception.")
        sys.exit(1)

    if mode == PrettyExceptionMode.RAISE:
        if exception is not None:
            raise DarwinException.from_exception(exception)
        raise DarwinException("Unknown error occurred.")
