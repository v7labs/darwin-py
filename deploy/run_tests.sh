#! /usr/bin/env bash
# Run unit tests
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - Unit tests failed

THIS_FILE_DIRECTORY=`dirname "$0"`

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <directory> [<python version> <os>]"
    exit 1
fi

if [ "$#" -eq 3 ]; then
    USING_CICD=1
    OS=$3
    PYTHON_VERSION=$2
fi

echo "Running unit tests in directory: $1"
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

# Unit test config is in pyproject.toml and pytest.ini - don't set any here as it will only complicate CI/CD
if [ "$USING_CICD" = 1 ]; then
    poetry run pytest $1 -vvv --junit-xml=$THIS_FILE_DIRECTORY/$PYTHON_VERSION-$OS-test_results.xml || exit 3
    exit 0
fi

poetry run pytest $1 || exit 3

echo "Unit tests passed"

exit 0
