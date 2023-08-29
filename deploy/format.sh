#! /usr/bin/env bash
# Check formatting
# This script is intended for CI/CD only
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - Black formatting failed

THIS_FILE_DIRECTORY=`dirname "$0"`
FILES_CHANGED="$1"

echo "Checking formatting of reference: $1"

if ! $CI; then
    echo "This script is intended for CI/CD only"
    exit 1
fi

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <git-ref>"
    exit 1
fi

echo "Checking formatting of files: $1"
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

echo "$1" | grep -E '\.py$' | xargs | poetry run black --check --diff --no-color . || exit 3