#!/usr/bin/env bash

ACTION=$1
shift 1
FILES=$@

echo "Action: $ACTION"
echo "Files: $FILES"

# If action is not format or lint exit
if [[ -z $ACTION || ($ACTION != "format" && $ACTION != "lint") ]] ; then
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
    pip install black &> pip_log.txt
else
    pip install flake8 flake8-pyproject &> pip_log.txt
fi

# Check if pip install failed
if [ $? -ne 0 ]; then
    echo "Pip install failed"
    cat pip_log.txt
    rm pip_log.txt
    exit 1
fi

failed_formatting=1
failed_files=""
echo "** Checking files [$FILES] **"

for file in $FILES
do
    echo "_________________________________________________________"
    echo "Checking $file"

    if [ -f $file ]; then
        if [ $ACTION == "lint" ]; then
            flake8 --config pyproject.toml $file || failed_formatting=$(failed_formatting + 1)\
            && failed_files="$failed_files $file"\
            && echo "Failed linting for $file"
        fi

        if [ $ACTION == "format" ]; then
            black --check $file || failed_formatting=$(failed_formatting + 1)\
            && failed_files="$failed_files $file"\
            && echo "Failed formatting for $file"
        fi
    else
        echo "File $file does not exist"
    fi

    echo "_________________________________________________________"
done

if [ $failed_formatting -ne 0 ]; then
    echo "Formatting failed for $failed_formatting files 😢"
    echo "Failed files"
    for file in $failed_files ; do
        echo "- $file"
    done
    exit 1
else
    echo "Formatting passed for all files 🎉"
fi
exit 0
