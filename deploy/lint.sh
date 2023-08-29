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
FILES_CHANGED="$@"

if ! $CI; then
    echo "This script is intended for CI/CD only"
    exit 1
fi

echo "Checking linting compliance"


if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <files-list>"
    exit 1
fi

EXIT_CODE=0

echo "Checking linting compliance of files: $FILES_CHANGED"
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

for file in $FILES_CHANGED; do
    if [[ $file == *"__init__.py"* ]]; then
        echo "Skipping __init__.py file: $file"
        continue
    fi
    if [[ $file != *.py ]]; then
        echo "Skipping non-python file: $file"
        continue
    fi

    echo "Checking flake8 compliance of file: $file"
    poetry run flake8 $file
    if $!; then
        echo "Flake8 check failed for file: $file"
        EXIT_CODE=$1!
    fi
done

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "Flake8 check passed"
else
    echo "Flake8 check failed"
fi

exit $EXIT_CODE