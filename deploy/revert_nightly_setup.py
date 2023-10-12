#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from os import path
from pathlib import Path


def main() -> None:
    new_package_name = "darwin-py"

    this_file_path = Path(__file__).parent.resolve()
    path_to_pyproject = this_file_path / ".." / "pyproject.toml"
    path_to_version = this_file_path / ".." / "version.txt"

    try:
        assert path_to_pyproject.exists()
        assert path_to_version.exists()
    except AssertionError:
        print("No nightly build in place to revert")
        exit(1)

    lines = path_to_pyproject.read_text().splitlines()
    new_version = path_to_version.read_text().strip()

    lines_to_write = []

    for line in lines:
        if line.startswith("name ="):
            line = f'name = "{new_package_name}"\n'
        if line.startswith("version ="):
            line = f'version = {new_version}\n'
        lines_to_write.append(line)

    path_to_pyproject.write_text("\n".join(lines_to_write))

    print(f"Changed package name to {new_package_name}@{new_version} in pyproject.toml")


if __name__ == "__main__":
    main()
