#!/usr/bin/env bash
# Check poetry is installed
if ! command -v poetry &> /dev/null
then
    echo "Poetry could not be found"
    exit 4
fi

exit 0