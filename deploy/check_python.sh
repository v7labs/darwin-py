#!/usr/bin/env bash
# Confirm that python 3.8 or higher is installed and pip installed

# Check python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python3 could not be found"
    exit 1
fi

# Check python version is 3.8  or higher
if [[ $(python3 -c 'import sys; print(sys.version_info >= (3, 8))') != "True" ]]
then
    echo "Python version 3.8 or higher is required"
    exit 2
fi

# Check pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found"
    exit 3
fi

exit 0