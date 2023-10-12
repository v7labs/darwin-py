#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Require a single string argument, the new package name
# Example: python change_package_name.py com.example.newname

from argparse import ArgumentParser

parser = ArgumentParser(description="Change package name in pyproject.toml")
parser.add_argument("new_package_name", type=str, help="New package name")


def main() -> None:
    args = parser.parse_args()
    new_package_name = args.new_package_name

    with open("pyproject.toml", "r") as f:
        lines = f.readlines()

    with open("pyproject.toml", "w") as f:
        for line in lines:
            if line.startswith("name ="):
                line = f'name = "{new_package_name}"\n'
            f.write(line)

    print(f"Changed package name to {new_package_name} in pyproject.toml")


if __name__ == "__main__":
    main()
