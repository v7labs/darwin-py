#! /usr/bin/env bash
# Check PEP8 compliance and other linting
# This script is intended for CI/CD, but can be run locally
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - PEP8 compliance failed

THIS_FILE_DIRECTORY=`dirname "$0"`
FILES_CHANGED="$1"

if ! $CI; then
    echo "This script is intended for CI/CD only"
    exit 1
fi

echo "Checking linting compliance of reference: $2 against $1"


if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <files-list>"
    exit 1
fi

echo "Checking linting compliance of files: $FILES_CHANGED"
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

echo "$FILES_CHANGED" | grep -E '\.py$' | xargs | poetry run flake8 --diff --no-color . || exit 3