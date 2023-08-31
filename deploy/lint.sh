#! /usr/bin/env bash
# Check PEP8 compliance and other linting
#
# Exit:
# 0 - Success
# 1 - Called with incorrect number of arguments
# 2 - Python3 or dependency not found
# 3 - PEP8 compliance failed

THIS_FILE_DIRECTORY=`dirname "$0"`
FILES_CHANGED="$@"

# Input checks
if ! $CI; then
    echo "This script is intended for CI/CD only"
    exit 1
fi
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <file>...<file>..."
    echo
    echo "Called with $@"
    exit 1
fi

# Introduction
echo
echo "Checking linting compliance"
echo
echo "These files were changed in this diff:"
echo $FILES_CHANGED | tr " " "\n"
echo
echo "** Checking formatting of files **"
echo

"$THIS_FILE_DIRECTORY"/check_python.sh || "$THIS_FILE_DIRECTORY"/install_deps.sh || exit 2

flake8_failed_files=""
number_of_python_files=0
skipped_files=0
skipped_init_files=0
nonexistent_files=0

for file in $FILES_CHANGED; do
    if [ ! -f "$file" ]; then
        skipped_files=$((skipped_files+1))
        nonexistent_files=$((nonexistent_files+1))
        continue
    fi
    if [[ $file == *"__init__.py"* ]]; then
        skipped_files=$((skipped_files+1))
        continue
    fi
    if [[ $file != *.py ]]; then
        skipped_files=$((skipped_files+1))
        continue
    fi
    
    echo "> Checking flake8 compliance of file: $file"
    number_of_python_files=$((number_of_python_files+1))
    
    poetry run flake8 $file
    if $!; then
        echo "Flake8 check failed for file: $file"
        flake8_failed_files="$flake8_failed_files $file"
    fi
done

if [[ $number_of_python_files -eq 0 ]]; then
    echo "No checkable python files found in input."
    exit 0
fi

if [[ $flake8_failed_files -eq "" ]]; then
    if [[ $number_of_python_files -eq 0 ]]; then
        echo "No checkable python files found in input."
    else
        echo "Black formatting passed"
    fi
    exit 0
else
    echo "** Black formatting failed **"
    echo "These files failed black formatting:"
    echo
    echo $flake8_failed_files | tr " " "\n"
    echo
    exit 3
fi