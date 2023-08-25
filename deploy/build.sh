#!/usr/bin/env bash

# Check python and pip are installed
echo "Check that python3 and pip3 are installed"
./deploy/check_python.sh || exit $?


echo "Check that poetry is installed"
if ! command -v poetry &> /dev/null
then
    # Try to run install deps script, and if that fails, exit gracefully
    echo "Poetry could not be found"
    echo "Installing dependencies"
    
    .deploy/install_deps.sh || exit 1
fi

# Check poetry is installed
if ! command -v poetry &> /dev/null
then
    echo "Poetry could not be found after dependency install"
    exit 2
fi

poetry build || exit 3


