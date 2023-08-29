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
FILES_CHANGED="$@"

if ! $CI; then
    echo "This script is intended for CI/CD only"
    exit 1
fi

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <file>...<file>..."
    exit 1
fi

echo "Checking formatting of files: $1"
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

EXIT_CODE=0

for file in $FILES_CHANGED; do
    if [[ $file == *"__init__.py"* ]]; then
        echo "Skipping __init__.py file: $file"
        continue
    fi
    if [[ $file != *.py ]]; then
        echo "Skipping non-python file: $file"
        continue
    fi

    echo "Checking black formatting of file: $file"
    poetry run black --check --diff --no-color $file
    if $!; then
        echo "Black formatting failed for file: $file"
        EXIT_CODE=$!
    fi
done

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "Black formatting passed"
else
    echo "Black formatting failed"
fi

exit $EXIT_CODE