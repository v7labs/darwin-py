import io
from pathlib import Path
from typing import Any, Callable, Optional, Union

from orjson import OPT_INDENT_2, OPT_PASSTHROUGH_DATACLASS, OPT_SERIALIZE_NUMPY
from orjson import dumps as orjson_dumps

DEFAULT_ENCODE_OPTIONS = OPT_INDENT_2 | OPT_SERIALIZE_NUMPY | OPT_PASSTHROUGH_DATACLASS


def dumps(
    obj: Any,
    default: Optional[Callable[[Any], Any]] = None,
    option: int = 0,
) -> str:
    """
    Serializes a Python object to a JSON formatted str using orjson.

    Defaults to using the following options:
    - OPT_INDENT_2
    - OPT_SERIALIZE_NUMPY
    - OPT_PASSTHROUGH_DATACLASS

    Parameters
    ----------
    obj : Any   Must be JSON serializable.  NumPy Objects are supported.
    default : Optional[Callable]   Can use to override the default JSON serializer.
    option: int  orjson options.  Import from orjson import OPT_INDENT_*.  Add using bitwise or |.

    Returns
    -------
    str  JSON formatted string.

    """
    option = option | DEFAULT_ENCODE_OPTIONS
    return orjson_dumps(obj, default, option).decode("utf-8")


def dump(
    obj: Any,
    file: Union[str, Path, io.TextIOWrapper],
    default: Optional[Callable[[Any], Any]] = None,
    option: int = 0,
) -> None:
    """
    Serializes a Python object to a JSON formatted str using orjson, and writes to a file.

    Defaults to using the following options:
    - OPT_INDENT_2
    - OPT_SERIALIZE_NUMPY
    - OPT_PASSTHROUGH_DATACLASS

    Parameters
    ----------
    obj : Any   Must be JSON serializable.  NumPy Objects are supported.
    file : Union[filename, Path, TextIOWrapper]  Filename, path, or file-handle from the open context manager, to write to.
    default : Optional[Callable]   Can use to override the default JSON serializer.
    option: int  orjson options.  Import from orjson import OPT_INDENT_*.  Add using bitwise or |.

    Returns
    -------
    None


    """

    if isinstance(file, str):
        with Path(file).open("w") as f:
            _write_to_handler(f, dumps(obj, default, option))

    elif isinstance(file, Path):
        with file.open("w") as f:
            _write_to_handler(f, dumps(obj, default, option))

    else:
        _write_to_handler(file, dumps(obj, default, option))


def _write_to_handler(file: io.TextIOWrapper, data: str):
    file.write(data)
