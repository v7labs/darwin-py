"""
Contains utility functions for a rich console.
"""

from typing import Iterable, List, Optional

from rich.progress import ProgressType, track
from rich.theme import Theme

from datatypes import AnnotationFile


def get_progress_bar(array: List[AnnotationFile], description: Optional[str] = None) -> Iterable[ProgressType]:
    """
    Get a rich a progress bar for the given list of annotation files.

    Parameters
    ----------
    array : List[dt.AnnotationFile]
        The list of annotation files.
    description : Optional[str], default: None
        A description to show above the progress bar.

    Returns
    -------
    Iterable[ProgressType]
        An iterable of ``ProgressType`` to show a progress bar.
    """
    if description:
        return track(array, description=description)
    return track(array)


def console_theme() -> Theme:
    return Theme({"success": "bold green", "warning": "bold yellow", "error": "bold red"})
