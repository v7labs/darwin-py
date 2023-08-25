#!/usr/bin/env bash
# This script installs dependencies for the project
# It is intended for CI/CD, but can be run locally
# It will exit at any point that fails, and will return different exit codes:
# 1 - Python3 not found
# 2 - Python version is not 3.8 or higher
# 3 - pip3 not found
# 4 - Poetry not found after attempted install
# 5 - pip3 upgrade failed
# 6 - Poetry install failed


echo "Installing dependencies"

# Check python is installed
./deploy/check_python.sh || exit $?

# Check poetry is installed, and install if not
if ! command -v poetry &> /dev/null
then
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Check poetry is installed
if ! command -v poetry &> /dev/null
then
    echo "Poetry could not be found"
    exit 4
fi

# Install dependencies
python3 -m pip install --upgrade pip || exit 5
python3 -m poetry install --all-extras --no-interaction --no-root || exit 6

echo "Dependencies installed"

exit 0