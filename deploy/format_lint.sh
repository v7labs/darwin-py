#!/usr/bin/env bash

ACTION=$1
shift 1
FILES=$@

echo "Action: $ACTION"
echo "Files: $FILES"

# If action is not format or lint exit
if [[ -z $ACTION || ("$ACTION" != "format" && "$ACTION" != "lint") ]] ; then
    echo "Action must be format or lint"
    exit 1
fi

# If no files are passed in, exit
if [[ -z $FILES ]]; then
    echo "No files passed in"
    exit 1
fi

# Install dependencies
if [ "$ACTION" == "format" ]; then
    pip install black &> pip_log.txt
else
    pip install ruff &> pip_log.txt
fi

# Check if pip install failed
if [ $? -ne 0 ]; then
    echo "Pip install failed"
    cat pip_log.txt
    rm pip_log.txt
    exit 1
fi

failed_files=""
echo "** Checking files [$FILES] **"

for file in $FILES ; do
    echo "_________________________________________________________"
    echo "Checking $file"

    if [ -f $file ]; then
        if [ "$ACTION" == "lint" ]; then
            ruff check $FILES; rc=$?
            echo "$rc"
            if [ $rc -ne 0 ]; then
                failed_files="$failed_files $file"
                echo "❌"
            else
                echo "✅"
            fi
        fi

        if [ "$ACTION" == "format" ]; then
            black --check $file
            if [ $? -ne 0 ]; then
                failed_files="$failed_files $file"
                echo "❌"
            else
                echo "✅"
            fi
        fi
    else
        echo "File $file does not exist"
    fi

    echo "DEBUG"
    echo "failed_files: $failed_files"

    echo "_________________________________________________________"
done

echo "$failed_files"

if [[ "$failed_files" -ne "" ]]; then
    echo "Checks failed for $failed_formatting files 😢"
    echo "Failed files"
    for file in $failed_files ; do
        echo "- $file"
    done
    exit 1
else
    echo "Formatting passed for all files 🎉"
fi
exit 0
