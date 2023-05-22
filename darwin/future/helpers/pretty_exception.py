import sys
from typing import Optional

from rich.console import Console

from darwin.future.exceptions.base import DarwinException


def pretty_exception(halt: bool = False, bubble: bool = True, frame_limit: int = 0) -> None:
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

    if halt:
        console.print("Halting execution due to exception.")
        sys.exit(1)

    if bubble:
        if exception is not None:
            raise DarwinException.from_exception(exception)
        raise DarwinException("Unknown error occurred.")
