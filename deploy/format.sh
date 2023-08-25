#! /usr/bin/env bash
# Check formatting
# This script is intended for CI/CD, but can be run locally
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - Black formatting failed

THIS_FILE_DIRECTORY=`dirname "$0"`

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <git-ref>"
    exit 1
fi

echo "Checking formatting of reference: $1"
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

git diff --name-only master.."$1" | grep -E '\.py$' | xargs | poetry run black --check --diff --no-color . || exit 3