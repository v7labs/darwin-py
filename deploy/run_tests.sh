#! /usr/bin/env bash
# Run unit tests
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Test directory does not exist
# 3 - Python3 or dependency not found
# 4 - Unit tests failed

THIS_FILE_DIRECTORY=$(dirname `realpath "$0"`)
TEST_DIRECTORY=`realpath "$THIS_FILE_DIRECTORY"/../tests`

if [ "$#" -gt 3 ]; then
    echo "Usage: $0 [<directory> <python version> <os>]"
    echo
    echo "Called with $@"
    exit 1
fi

if [ "$#" -eq 3 ]; then
    echo "Called with directory and versions, so assuming CI/CD"
    USING_CICD=1
    TEST_DIRECTORY=$1
    OS=$3
    PYTHON_VERSION=$2
else
    echo "Called without directory and versions, so calculating test directory"
fi

if [ ! -d "$TEST_DIRECTORY" ]; then
    echo "Test directory does not exist"
    exit 2
fi

echo "Running unit tests in directory: $TEST_DIRECTORY"

"$THIS_FILE_DIRECTORY"/check_poetry.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 3

# Unit test config is in pyproject.toml and pytest.ini - don't set any here as it will only complicate CI/CD
if [ "$USING_CICD" = 1 ]; then
    poetry run pytest $TEST_DIRECTORY -vvv --junit-xml=$THIS_FILE_DIRECTORY/$PYTHON_VERSION-$OS-test_results.xml || exit 3
    exit 0
fi

poetry run pytest $TEST_DIRECTORY || exit 4

echo "Unit tests passed"

exit 0
