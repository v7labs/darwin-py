#!/usr/bin/env bash

ACTION=$1
shift 1
FILES=$@

echo "Action: $ACTION"
echo "Files: $FILES"

# If action is not format or lint exit
if [[ -z $ACTION || ("$ACTION" != "format" && "$ACTION" != "lint" && "$ACTION" != "typecheck") ]] ; then
    echo "Action must be format, typecheck, or lint"
    exit 1
fi

# If no files are passed in, exit
if [[ -z $FILES ]]; then
    echo "No files passed in"
    exit 1
fi

# Install dependencies
pipinstall() {
    if ! pip install "$@" &> pip_log.txt; then
        echo "Pip install failed"
        cat pip_log.txt
        rm pip_log.txt
        exit 1
    fi
}

if [ "$ACTION" == "format" ]; then
    pipinstall black
    elif [ "$ACTION" == "lint" ]; then
    pipinstall ruff
    elif [ "$ACTION" == "typecheck" ]; then
    pipinstall mypy
else
    echo "Action must be format, typecheck, or lint"
    exit 1
fi

failed_files=""
echo "** Checking files [$FILES] **"

for file in $FILES ; do

    if [[ ! -f $file ]]; then
        echo
        echo "📁 Skipping file $file, file doesn't exist.  Was probably removed in PR diff."
        continue
    fi

    echo "_________________________________________________________"
    echo
    echo "Checking $file"


    if [ "$ACTION" == "lint" ]; then

        if ! ruff check "$file"; then
            failed_files="$failed_files $file"
            echo "❌"
        else
            echo "✅"
        fi
    fi

    if [ "$ACTION" == "typecheck" ]; then

        if ! mypy "$file"; then
            failed_files="$failed_files $file"
            echo "❌"
        else
            echo "✅"
        fi
    fi

    if [ "$ACTION" == "format" ]; then

        if ! black --check "$file"; then
            failed_files="$failed_files $file"
            echo "❌"
        else
            echo "✅"
        fi
    fi

    echo "_________________________________________________________"
done

echo
echo

if [[ "$failed_files" != "" ]]; then
    echo "Checks failed for $failed_files files 😢"
    echo "Failed files"
    for file in $failed_files ; do
        echo "- $file"
    done
    exit 1
else
    echo "$ACTION passed for all files 🎉"
fi
exit 0
