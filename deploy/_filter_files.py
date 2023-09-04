#!/usr/bin/env python3

import sys
from typing import List


def main(argv: List[str]) -> None:
    file_extension: str = argv[0]
    files_in: List[str] = argv[1:]

    if file_extension.startswith("."):
        file_extension = file_extension[1:]

    files_out = [file for file in files_in if file.endswith(f".{file_extension}")]

    print(" ".join(files_out))


if __name__ == "__main__":
    main(sys.argv[1:])
