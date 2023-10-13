#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Require a single string argument, the new package name
# Example: python change_package_name.py com.example.newname

from datetime import datetime
from os import linesep
from pathlib import Path


def main() -> None:
    epoch_timestring = datetime.now().strftime("%s")

    this_file_path = Path(__file__).parent.resolve()
    path_to_pyproject = this_file_path / ".." / "pyproject.toml"
    path_to_version = this_file_path / ".." / "version.txt"

    try:
        assert path_to_pyproject.exists()
    except AssertionError:
        print("No pyproject.toml found.")
        exit(1)

    lines = path_to_pyproject.read_text().splitlines()
    lines_to_write = []

    for line in lines:
        if line.startswith("name ="):
            lines_to_write.append('name = "darwin-nightly"\n')
        elif line.startswith("version ="):
            version = line.split("=")[1].strip()
            path_to_version.write_text(version)
            lines_to_write.append(f'version = "{epoch_timestring}"\n')
        else:
            lines_to_write.append(line)

    path_to_pyproject.write_text(linesep.join(lines_to_write))

    print(f"Set build to a nightly in pyproject.toml - darwin-nightly@{epoch_timestring}")


if __name__ == "__main__":
    main()
