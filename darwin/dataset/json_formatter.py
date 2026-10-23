"""Format JSON with bounded buffers without changing string or number tokens."""

import os
import re
import stat
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import IO


class PrettyPrintError(Exception):
    """A local JSON file could not be formatted and retains its original bytes."""


_CHUNK_SIZE = 64 * 1024
_STRING_SPECIAL = re.compile(r'["\\\x00-\x1f]')
_WHITESPACE = re.compile(r"[ \t\r\n]*")
_DIGITS = re.compile(r"[0-9]*")


class _Reader:
    def __init__(self, source: IO[str]) -> None:
        self.source = source
        self.buffer = ""
        self.offset = 0

    def peek(self) -> str:
        if self.offset == len(self.buffer):
            self.buffer = self.source.read(_CHUNK_SIZE)
            self.offset = 0
        return self.buffer[self.offset : self.offset + 1]

    def take(self) -> str:
        char = self.peek()
        self.offset += bool(char)
        return char

    def skip_whitespace(self) -> None:
        while self.peek():
            match = _WHITESPACE.match(self.buffer, self.offset)
            assert match is not None
            self.offset = match.end()
            if self.offset < len(self.buffer):
                return

    def copy_digits(self, output: IO[str]) -> None:
        while self.peek():
            match = _DIGITS.match(self.buffer, self.offset)
            assert match is not None
            end = match.end()
            output.write(self.buffer[self.offset : end])
            self.offset = end
            if end < len(self.buffer):
                return


def _copy_string(reader: _Reader, output: IO[str]) -> None:
    output.write(reader.take())
    while reader.peek():
        match = _STRING_SPECIAL.search(reader.buffer, reader.offset)
        end = match.start() if match else len(reader.buffer)
        output.write(reader.buffer[reader.offset : end])
        reader.offset = end
        if match is None:
            continue
        char = reader.take()
        if char == '"':
            output.write(char)
            return
        if char != "\\":
            raise ValueError("Unescaped control character in string")
        escape = reader.take()
        if escape == "u":
            output.write("\\u")
            for _ in range(4):
                digit = reader.take()
                if not digit or digit not in "0123456789abcdefABCDEF":
                    raise ValueError("Invalid Unicode escape in string")
                output.write(digit)
        elif escape and escape in '"\\/bfnrt':
            output.write("\\" + escape)
        else:
            raise ValueError("Invalid escape in string")
    raise ValueError("Unterminated string")


def _copy_number(reader: _Reader, output: IO[str]) -> None:
    if reader.peek() == "-":
        output.write(reader.take())
    char = reader.peek()
    if char == "0":
        output.write(reader.take())
    elif char and char in "123456789":
        reader.copy_digits(output)
    else:
        raise ValueError("Expected a digit in number")
    if reader.peek() == ".":
        output.write(reader.take())
        if not reader.peek() or reader.peek() not in "0123456789":
            raise ValueError("Expected a digit after decimal point")
        reader.copy_digits(output)
    if reader.peek() and reader.peek() in "eE":
        output.write(reader.take())
        if reader.peek() and reader.peek() in "+-":
            output.write(reader.take())
        if not reader.peek() or reader.peek() not in "0123456789":
            raise ValueError("Expected a digit in exponent")
        reader.copy_digits(output)


class _State(Enum):
    VALUE = auto()
    ARRAY_FIRST = auto()
    ARRAY_VALUE = auto()
    OBJECT_FIRST = auto()
    OBJECT_KEY = auto()
    COLON = auto()
    OBJECT_VALUE = auto()
    COMMA_OR_END = auto()
    COMPLETE = auto()


@dataclass
class _Container:
    closing: str
    state: _State


def _format_json(source: IO[str], output: IO[str]) -> None:
    reader = _Reader(source)
    containers = [_Container("", _State.VALUE)]
    while containers:
        reader.skip_whitespace()
        char = reader.peek()
        current = containers[-1]
        state = current.state
        if state == _State.COMPLETE:
            if char:
                raise ValueError("Unexpected content after JSON value")
            output.write("\n")
            return
        if not char:
            raise ValueError("Unexpected end of JSON")

        if state == _State.COMMA_OR_END:
            if char == ",":
                output.write(reader.take())
                current.state = (
                    _State.OBJECT_KEY if current.closing == "}" else _State.ARRAY_VALUE
                )
                continue
            if char != current.closing:
                raise ValueError("Expected a comma or the end of a container")
            output.write("\n" + "  " * (len(containers) - 2))
        elif state in (_State.ARRAY_FIRST, _State.OBJECT_FIRST):
            if char != current.closing:
                current.state = (
                    _State.OBJECT_KEY if current.closing == "}" else _State.ARRAY_VALUE
                )
                continue
        elif state == _State.COLON:
            if char != ":":
                raise ValueError("Expected a colon after object key")
            reader.take()
            output.write(": ")
            current.state = _State.OBJECT_VALUE
            continue
        elif state == _State.OBJECT_KEY:
            if char != '"':
                raise ValueError("Expected a quoted object key")
            output.write("\n" + "  " * (len(containers) - 1))
            _copy_string(reader, output)
            current.state = _State.COLON
            continue
        else:
            if state == _State.ARRAY_VALUE:
                output.write("\n" + "  " * (len(containers) - 1))
            current.state = _State.COMMA_OR_END if current.closing else _State.COMPLETE
            if char in "[{":
                output.write(reader.take())
                containers.append(
                    _Container(
                        "}" if char == "{" else "]",
                        _State.OBJECT_FIRST if char == "{" else _State.ARRAY_FIRST,
                    )
                )
            elif char == '"':
                _copy_string(reader, output)
            elif char in "-0123456789":
                _copy_number(reader, output)
            elif char in "tfn":
                literal = {"t": "true", "f": "false", "n": "null"}[char]
                for expected in literal:
                    if reader.take() != expected:
                        raise ValueError("Invalid JSON literal")
                output.write(literal)
            else:
                raise ValueError("Expected a JSON value")
            continue

        output.write(reader.take())
        containers.pop()


def pretty_print_json(path: Path) -> None:
    """Atomically indent one UTF-8 JSON file while preserving all value tokens.

    Uses fixed input/output buffers plus container nesting state. The temporary
    output requires space next to the original file until replacement succeeds.
    """
    temporary_path = None
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        with path.open("r", encoding="utf-8", newline="") as source:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=path.parent,
                prefix=".darwin-pretty-print-",
                suffix=".tmp",
                delete=False,
            ) as output:
                temporary_path = Path(output.name)
                _format_json(source, output.file)
        temporary_path.chmod(mode)
        os.replace(temporary_path, path)
    except (OSError, UnicodeError, ValueError) as error:
        raise PrettyPrintError(
            f"Could not pretty-print '{path}': {error}. The original file is unchanged."
        ) from error
    finally:
        if temporary_path is not None:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)
