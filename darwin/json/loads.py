import io
from pathlib import Path
from typing import Any, Union

from orjson import loads as orjson_loads

DEFAULT_DECODE_OPTIONS = 0


def loads(input: Union[bytes, bytearray, memoryview, str]) -> Any:
    """
    Deserializes a JSON formatted str to a Python object using orjson.

    Parameters
    ----------

    input : Union[bytes, bytearray, memoryview, str]  JSON formatted string.

    Returns
    -------
    Any  Python object.
    """
    return orjson_loads(input)


def load(file: Union[str, Path, io.TextIOWrapper]) -> Any:
    """
    Deserialises JSON input from a file to a Python object using orjson.

    Parameters
    ----------
    file : Union[filename, Path, TextIOWrapper]  Filename, path, or file-handle from the open context manager, to read from.

    Returns
    -------
    Any  Python object.
    """
    if isinstance(file, io.TextIOWrapper):
        return loads(_read_from_handler(file))

    if isinstance(file, Path):
        with file.open() as f:
            return loads(_read_from_handler(f))

    if isinstance(file, str):
        with Path(file).open() as f:
            return loads(_read_from_handler(f))


def _read_from_handler(handle):
    return handle.read()
