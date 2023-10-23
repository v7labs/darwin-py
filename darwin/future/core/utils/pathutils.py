import json
from pathlib import Path
from typing import Optional

import yaml

from darwin.future.exceptions import UnrecognizableFileEncoding

ENCODINGS = ["utf-8", "utf-16", "utf-32", "ascii"]


def attempt_open(path: Path) -> dict:
    try:
        if "yaml" in path.suffix.lower():
            return open_yaml(path)
        elif "json" in path.suffix.lower():
            return open_json(path)
    except Exception:
        pass
    for encoding in ENCODINGS:
        try:
            if "yaml" in path.suffix.lower():
                return open_yaml(path, encoding)
            elif "json" in path.suffix.lower():
                return open_json(path, encoding)
        except Exception:
            pass
    raise UnrecognizableFileEncoding(
        f"Unable to load file {path} with any encodings: {ENCODINGS}"
    )


def open_yaml(path: Path, encoding: Optional[str] = None) -> dict:
    if not encoding:
        with path.open() as infile:
            data = yaml.safe_load(infile)
        return data
    with path.open(encoding=encoding) as infile:
        data = yaml.safe_load(infile)
    return data


def open_json(path: Path, encoding: Optional[str] = None) -> dict:
    if not encoding:
        with path.open() as infile:
            data = json.load(infile)
        return data

    with path.open(encoding=encoding) as infile:
        data = json.load(infile)
    return data
