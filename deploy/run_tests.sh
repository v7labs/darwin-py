#! /usr/bin/env bash
# Run unit tests
# This script is intended for CI/CD, but can be run locally
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - Unit tests failed

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

echo "Running unit tests in directory: $1"
./check_python.sh || ./install_deps.sh || exit 2

python3 -m poetry run pytest --cov="$1" --cov-report=xml --cov-report=term-missing --cov-fail-under=85 "$1" || exit 3

echo "Unit tests passed"

exit 0
