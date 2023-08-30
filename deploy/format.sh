#! /usr/bin/env bash
# Check formatting
# This script is intended for CI/CD only
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - Black formatting failed

THIS_FILE_DIRECTORY=`dirname "$0"`
FILES_CHANGED="$@"

# Input checks
if ! $CI; then
    echo "This script is intended for CI/CD only"
    exit 1
fi

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <file>...<file>..."
    exit 1
fi

# Introduction
echo
echo "** Checking formatting **"
echo
echo "These files were changed in this diff:"
echo $FILES_CHANGED | tr " " "\n"
echo
echo "** Checking formatting of files **"
echo

# Check dependencies
"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

EXIT_CODE=0
NUMBER_OF_PYTHON_FILES=0
SKIPPED_FILES=0
NONEXISTENT_FILES=0
for file in $FILES_CHANGED; do
    if [ ! -f "$file" ]; then
        SKIPPED_FILES=$((SKIPPED_FILES+1))
        NONEXISTENT_FILES=$((NONEXISTENT_FILES+1))
        continue
    fi
    
    if [[ $file == *"__init__.py"* ]]; then
        SKIPPED_FILES=$((SKIPPED_FILES+1))
        continue
    fi
    
    if [[ $file != *.py ]]; then
        SKIPPED_FILES=$((SKIPPED_FILES+1))
        continue
    fi
    
    echo "> Checking black formatting of file: $file"
    poetry run black --check --diff --no-color $file
    NUMBER_OF_PYTHON_FILES=$((NUMBER_OF_PYTHON_FILES+1))
    if $!; then
        echo ">...Black formatting failed for file: $file"
        EXIT_CODE=$!
    fi
    echo
done

echo "Done."
echo "Checked $NUMBER_OF_PYTHON_FILES python files"
echo "Skipped $SKIPPED_FILES files"
echo "Skipped $NONEXISTENT_FILES files that do not exist"

if [[ $NUMBER_OF_PYTHON_FILES -eq 0 ]]; then
    echo "No checkable python files found in input."
    exit 0
fi

if [[ $EXIT_CODE -eq 0 ]]; then
    if [[ $NUMBER_OF_PYTHON_FILES -eq 0 ]]; then
        echo "No checkable python files found in input."
    else
        echo "Black formatting passed"
    fi
    exit 0
else
    echo "Black formatting failed"
    exit 3
fi