#!/bin/bash

# Usage
# To install the typechecking linters, simply run the script in your terminal:

# sh
# This will install the linters and set up the pre-commit hook to run them on each changed Python file.
# -o, --post-commit, -p, --pre-commit, default -o post commit install

# Requirements
# This script requires the following tools to be installed:

# Git
# Black
# Ruff
# Mypy
# Make sure these tools are installed and available in your system's PATH before running the script.

# Define the hook script
HOOK_SCRIPT="#!/bin/bash
# Get the list of changed Python files in the darwin/future folder
FILES=\$(git diff --diff-filter=MA --name-only master | grep 'darwin/future/.*\.py$')
RED='\033[0;31m'
GREEN='\033[0;32m'
echo Pre-Commit Hook: Typecheck
echo ----------------------------------------
echo checking \$FILES
# Run the linters on each changed file
echo \nRunning Black
echo ----------------------------------------
BLACK_FAILED=0
black --check \$FILES || BLACK_FAILED=1

echo \nRunning Ruff
echo ----------------------------------------
RUFF_FAILED=0
ruff check \$FILES || RUFF_FAILED=1

echo \nRunning Mypy
echo ----------------------------------------
MYPY_FAILED=0
mypy \$FILES || MYPY_FAILED=1

# Check if any linter failed
echo \nSummary
echo ----------------------------------------
if [ \$BLACK_FAILED -eq 1 ]; then
    echo \"${RED}Black failed.\"
fi
if [ \$RUFF_FAILED -eq 1 ]; then
    echo \"${RED}Ruff failed.\"
fi
if [ \$MYPY_FAILED -eq 1 ]; then
    echo \"${RED}Mypy failed.\"
fi
if [ \$BLACK_FAILED -eq 0 ] && [ \$RUFF_FAILED -eq 0 ] && [ \$MYPY_FAILED -eq 0 ]; then
    echo \"${GREEN}All linters passed.\"
fi
"

# Define the hook name
HOOK_NAME="linters"

# Define the hook directory
HOOK_DIR="$(git rev-parse --show-toplevel)/.git/hooks"

# Define the hook file names
PRE_COMMIT_FILE="$HOOK_DIR/pre-commit"
POST_COMMIT_FILE="$HOOK_DIR/post-commit"

# Define the hook file names with the hook name
PRE_COMMIT_HOOK_FILE="$HOOK_DIR/pre-commit"
POST_COMMIT_HOOK_FILE="$HOOK_DIR/post-commit"

# Define the default hook file name
DEFAULT_HOOK_FILE="$POST_COMMIT_FILE"

# Define the default hook type
DEFAULT_HOOK_TYPE="post-commit"

# Parse the command line arguments
while [[ $# -gt 0 ]]
do
    key="$1"

    case $key in
        -p|--pre-commit)
        DEFAULT_HOOK_FILE="$PRE_COMMIT_FILE"
        DEFAULT_HOOK_TYPE="pre-commit"
        shift
        ;;
        -o|--post-commit)
        DEFAULT_HOOK_FILE="$POST_COMMIT_FILE"
        DEFAULT_HOOK_TYPE="post-commit"
        shift
        ;;
        *)
        echo "Unknown option: $key"
        exit 1
        ;;
    esac
done

# Create the hook file
echo "$HOOK_SCRIPT" > "$DEFAULT_HOOK_FILE"

# Make the hook file executable
chmod +x "$DEFAULT_HOOK_FILE"

# # Install the hook file
# if [ -f "$DEFAULT_HOOK_FILE" ]; then
#     mv "$DEFAULT_HOOK_FILE" "$HOOK_DIR/$DEFAULT_HOOK_TYPE-$(date +%s)-$HOOK_NAME"
# fi
# ln -s "$PRE_COMMIT_HOOK_FILE" "$DEFAULT_HOOK_FILE"
