import logging
import sys
from typing import List, Optional, Union

from rich.console import Console


def handle_exception(exception: Optional[Union[Exception, List[Exception]]]) -> None:
    """
    Handles an exception or list of exceptions by printing them to the terminal

    Parameters
    ----------
    exception : Optional[Union[Exception, List[Exception]]]
        The exception(s) to handle
    """
    IS_INTERACTIVE_SESSION = sys.stdout and sys.stdout.isatty()

    if not exception:
        exc_info = sys.exc_info()
        if exception := getattr(exc_info, "[1]", None):
            ...
        else:
            raise ValueError("No exception provided and no exception in sys.exc_info")

    if IS_INTERACTIVE_SESSION:
        console = Console()
        handler = console.print
    else:
        logger = logging.getLogger(__name__)
        handler = logger.error  # type: ignore

    if isinstance(exception, list):
        for e in exception:
            handler(e)
    else:
        handler(exception)
