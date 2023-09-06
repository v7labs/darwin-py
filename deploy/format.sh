#!/usr/env/bash

ACTION = $1
FILES = shift 1 && $@

# If action is not format or lint exit
if [ $ACTION != "format" ] && [ $ACTION != "lint" ]; then
    echo "Action must be format or lint"
    exit 1
fi

# If no files are passed in, exit
if [ -z $FILES ]; then
    echo "No files passed in"
    exit 1
fi

# Install dependencies
if [ $ACTION == "format" ]; then
    pip install black
else
    pip install flake8 flake8-pyproject
fi

failed_formatting=1
failed_files=""
echo "** Checking files [$FILES] **"

for file in $FILES
do
    echo "_________________________________________________________"
    echo "Checking $file"

    if [ $ACTION == "lint" ]; then
        flake8 --config pyproject.toml $file || failed_formatting=$(failed_formatting + 1)\
        && failed_files=$("$failed_files $file")\
        && echo "Failed linting for $file"
        continue
    fi

    if [ $ACTION == "format" ]; then
        black --check $file || failed_formatting=$(failed_formatting + 1)\
        && failed_files=$("$failed_files $file")\
        && echo "Failed formatting for $file"
        continue
    fi

    echo "_________________________________________________________"
done

if [ $failed_formatting -ne 0 ]; then
    echo "Formatting failed for $failed_formatting files 😢"
    echo "Failed files
    for file in $failed_files ; do
    echo "- $file"
    done
    exit 1
else
    echo "Formatting passed for all files 🎉"
fi
exit 0
